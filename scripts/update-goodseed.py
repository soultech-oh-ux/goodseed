#!/usr/bin/env python3
"""Goodseed official-release updater: verified, side-by-side installation."""
from pathlib import Path, PurePosixPath
import argparse, datetime, hashlib, json, os, re, shutil, stat, sys, tempfile
import urllib.request, urllib.parse, zipfile

REPO = 'soultech-oh-ux/goodseed'
API = f'https://api.github.com/repos/{REPO}/releases?per_page=30'
PREFIX = f'https://github.com/{REPO}/releases/download/'
HOSTS = {'api.github.com','github.com','release-assets.githubusercontent.com','objects.githubusercontent.com','github-releases.githubusercontent.com'}
MAX_BYTES = 1024 * 1024 * 1024
REQUIRED = ('Goodseed.exe','gsd.exe','gsdd.exe','WebView2Loader.dll','pack.tar.gz','pack-manifest.json','update-goodseed.py','runtime/python/python3.exe')


def version_key(tag):
    m = re.fullmatch(r'v?(\d+)\.(\d+)\.(\d+)(?:-([A-Za-z0-9.-]+))?', tag)
    if not m:
        raise ValueError('Unsupported version tag: '+tag)
    pre = m.group(4)
    parts = tuple((0,int(x)) if x.isdigit() else (1,x) for x in (pre or '').split('.'))
    return tuple(map(int,m.group(1,2,3))) + (pre is None, parts)


def validate_url(url):
    u = urllib.parse.urlsplit(url)
    if u.scheme != 'https' or u.hostname not in HOSTS or u.username or u.password:
        raise ValueError('Untrusted update URL')


class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_url(newurl)
        return super().redirect_request(req,fp,code,msg,headers,newurl)


def open_url(url):
    validate_url(url)
    req=urllib.request.Request(url,headers={'User-Agent':'Goodseed-Updater','Accept':'application/vnd.github+json' if url.startswith('https://api.github.com/') else 'application/octet-stream'})
    return urllib.request.build_opener(SafeRedirect).open(req,timeout=45)


def select_release(releases, allow_preview):
    candidates=[]
    for release in releases:
        if release.get('draft') or (release.get('prerelease') and not allow_preview):
            continue
        try:key=version_key(release['tag_name'])
        except (KeyError,ValueError):continue
        names={x.get('name') for x in release.get('assets',[])}
        if 'SHA256SUMS.txt' in names and any(re.fullmatch(r'Goodseed-\d+\.\d+\.\d+-Windows-x64\.zip',n or '') for n in names):
            candidates.append((key,release))
    if not candidates:
        raise ValueError('No compatible release found')
    return max(candidates,key=lambda x:x[0])[1]


def checksum_for(manifest, filename):
    for line in manifest.splitlines():
        m=re.fullmatch(r'([0-9a-fA-F]{64})\s+\*?(.+)',line.strip())
        if m and m.group(2)==filename:
            return m.group(1).lower()
    raise ValueError('Archive checksum is missing from SHA256SUMS.txt')


def download(url, dest, limit=MAX_BYTES):
    if not url.startswith(PREFIX):
        raise ValueError('Asset does not belong to the official release path')
    count=0
    digest=hashlib.sha256()
    with open_url(url) as response, dest.open('wb') as output:
        while block:=response.read(1024*1024):
            count+=len(block)
            if count>limit:raise ValueError('Download size limit exceeded')
            digest.update(block);output.write(block)
    return digest.hexdigest()


def extract_verified(archive, destination, expected_root):
    destination=destination.resolve()
    total=0
    with zipfile.ZipFile(archive) as z:
        for info in z.infolist():
            name=info.filename.replace('\\','/')
            p=PurePosixPath(name)
            if p.is_absolute() or '..' in p.parts or not p.parts or p.parts[0]!=expected_root or ':' in name or '\0' in name:
                raise ValueError('Unsafe archive path: '+name)
            if any(part.endswith((' ','.')) for part in p.parts):
                raise ValueError('Ambiguous Windows archive path')
            if stat.S_ISLNK(info.external_attr >> 16):
                raise ValueError('Archive symlinks are not supported')
            total+=info.file_size
            if total>3*MAX_BYTES:raise ValueError('Expanded archive size limit exceeded')
            target=(destination/Path(*p.parts)).resolve()
            if not target.is_relative_to(destination):raise ValueError('Archive escaped staging directory')
            if info.is_dir():target.mkdir(parents=True,exist_ok=True)
            else:
                target.parent.mkdir(parents=True,exist_ok=True)
                with z.open(info) as src,target.open('wb') as dst:shutil.copyfileobj(src,dst)
    result=destination/expected_root
    missing=[name for name in REQUIRED if not (result/name).is_file()]
    if missing:raise ValueError('Incomplete package: '+', '.join(missing))
    return result


def write_launchers(base, folder):
    if not re.fullmatch(r'Goodseed-\d+\.\d+\.\d+-Windows-x64(?:-[a-f0-9]{8})?',folder):
        raise ValueError('Invalid installation directory name')
    commands={
        'Start-Goodseed.cmd':f'@echo off\r\ncd /d "%~dp0"\r\nstart "" /D "%~dp0" "%~dp0{folder}\\Goodseed.exe"\r\n',
        'Upgrade-Goodseed.cmd':f'@echo off\r\n"%~dp0{folder}\\gsd.exe" update %*\r\npause\r\n',
    }
    for name,content in commands.items():
        target=base/name
        if target.exists():
            backup=base/'.goodseed-upgrade-backups'
            backup.mkdir(exist_ok=True)
            stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M%S-%f')
            shutil.copy2(target,backup/(stamp+'-'+name))
        tmp=base/(name+'.new')
        tmp.write_bytes(content.encode('ascii'))
        tmp.replace(target)


def install_archive(archive, base, expected_root, release):
    base=base.resolve()
    stage=Path(tempfile.mkdtemp(prefix='.gsd-update-',dir=base))
    try:
        payload=extract_verified(archive,stage,expected_root)
        target=base/expected_root
        if target.exists():
            target=base/(expected_root+'-'+os.urandom(4).hex())
        if payload.resolve().parent!=stage.resolve() or target.parent.resolve()!=base:
            raise ValueError('Installation target escaped expected directory')
        payload.rename(target)
        (target/'release-info.json').write_text(json.dumps({'tag':release['tag_name'],'version':'.'.join(map(str,version_key(release['tag_name'])[:3]))},indent=2),encoding='utf-8')
        write_launchers(base,target.name)
        return target
    finally:
        resolved=stage.resolve()
        if resolved.parent==base and resolved.name.startswith('.gsd-update-'):
            shutil.rmtree(resolved)


def run(args):
    install=Path(args.install_dir).resolve()
    info=install/'release-info.json'
    current=json.loads(info.read_text(encoding='utf-8-sig'))['tag'] if info.exists() else args.current_version
    with open_url(API) as response:
        raw=response.read(5*1024*1024+1)
        if len(raw)>5*1024*1024:raise ValueError('Release metadata is too large')
        releases=json.loads(raw)
    release=select_release(releases,args.preview or '-' in current)
    latest=release['tag_name']
    print(f'Installed: {current}\nAvailable: {latest}',flush=True)
    if version_key(latest)<=version_key(current):
        print('Already up to date.');return
    if args.check:
        print('Update available. Run gsd update to install.');return
    assets={x['name']:x for x in release['assets']}
    ver='.'.join(map(str,version_key(latest)[:3]))
    filename=f'Goodseed-{ver}-Windows-x64.zip'
    if filename not in assets:raise ValueError('Version-matching Windows package is missing')
    base=install.parent
    # Keep downloads outside the running install directory; clean only this owned temp directory.
    temp=Path(tempfile.mkdtemp(prefix='.gsd-download-',dir=base))
    try:
        sums=temp/'SHA256SUMS.txt'
        download(assets['SHA256SUMS.txt']['browser_download_url'],sums,1024*1024)
        expected=checksum_for(sums.read_text(encoding='utf-8-sig'),filename)
        print('Downloading Windows package...',flush=True)
        archive=temp/filename
        actual=download(assets[filename]['browser_download_url'],archive)
        if actual!=expected:raise ValueError('SHA-256 mismatch; update was not installed')
        print('SHA-256 verified. Installing to a new folder...',flush=True)
        target=install_archive(archive,base,filename[:-4],release)
    finally:
        resolved=temp.resolve()
        if resolved.parent==base.resolve() and resolved.name.startswith('.gsd-download-'):
            shutil.rmtree(resolved)
    print('Installed: '+str(target))
    print('Current sessions were not stopped. Close Goodseed when ready, then run Start-Goodseed.cmd to use the update.')


if __name__=='__main__':
    ap=argparse.ArgumentParser(description='Verified Goodseed release updater')
    ap.add_argument('--install-dir',required=True)
    ap.add_argument('--current-version',required=True)
    ap.add_argument('--check',action='store_true')
    ap.add_argument('--preview',action='store_true')
    try:run(ap.parse_args())
    except Exception as exc:
        print('Update failed: '+str(exc),file=sys.stderr)
        raise SystemExit(1)
