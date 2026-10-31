import importlib.util,hashlib,os,shutil,stat,tempfile,unittest,zipfile,io,json
from unittest import mock
from types import SimpleNamespace
from pathlib import Path
spec=importlib.util.spec_from_file_location('gsd_update',Path(__file__).with_name('update-goodseed.py'))
u=importlib.util.module_from_spec(spec);spec.loader.exec_module(u)

class UpdateTests(unittest.TestCase):
 def setUp(self):
  self.base=Path(tempfile.gettempdir()).resolve()
  self.root=Path(tempfile.mkdtemp(prefix='gsd-updater-test-',dir=self.base))
 def tearDown(self):
  target=self.root.resolve()
  assert target.parent==self.base and target.name.startswith('gsd-updater-test-')
  shutil.rmtree(target)
 def archive(self,extras=None):
  f=self.root/'package.zip';name='Goodseed-0.1.2-Windows-x64'
  with zipfile.ZipFile(f,'w') as z:
   for path in u.REQUIRED:z.writestr(name+'/'+path,b'test fixture')
   for path,data in (extras or []):z.writestr(path,data)
  return f,name
 def test_versions_and_prerelease_selection(self):
  self.assertLess(u.version_key('v0.1.2-preview.9'),u.version_key('v0.1.2'))
  self.assertLess(u.version_key('v0.1.2-preview.2'),u.version_key('v0.1.2-preview.10'))
  releases=[{'tag_name':'v0.1.1','prerelease':False,'assets':[{'name':'SHA256SUMS.txt'},{'name':'Goodseed-0.1.1-Windows-x64.zip'}]}, {'tag_name':'v0.1.2-preview.1','prerelease':True,'assets':[{'name':'SHA256SUMS.txt'},{'name':'Goodseed-0.1.2-Windows-x64.zip'}]}]
  self.assertEqual(u.select_release(releases,False)['tag_name'],'v0.1.1')
  self.assertEqual(u.select_release(releases,True)['tag_name'],'v0.1.2-preview.1')
 def test_manifest_and_official_url_validation(self):
  digest=hashlib.sha256(b'fixture').hexdigest()
  self.assertEqual(u.checksum_for(digest+'  program.zip','program.zip'),digest)
  with self.assertRaises(ValueError):u.checksum_for('bad  program.zip','program.zip')
  for bad in ['http://github.com/x','https://evil.example/x','https://github.com@evil.example/x']:
   with self.assertRaises(ValueError):u.validate_url(bad)
 def test_extract_and_side_by_side_install_preserve_current_files(self):
  archive,name=self.archive();old=self.root/'Goodseed-0.1.1-Windows-x64';old.mkdir();(old/'active.txt').write_text('keep')
  target=u.install_archive(archive,self.root,name,{'tag_name':'v0.1.2-preview.1'})
  self.assertTrue((target/'Goodseed.exe').exists())
  self.assertEqual((old/'active.txt').read_text(),'keep')
  self.assertIn(name,(self.root/'Start-Goodseed.cmd').read_text())
  self.assertIn('gsd.exe',(self.root/'Upgrade-Goodseed.cmd').read_text())
  self.assertFalse(any(p.name.startswith('.gsd-update-') for p in self.root.iterdir()))
 def test_traversal_and_drive_paths_rejected(self):
  for unsafe in ['../escape.txt','Goodseed-0.1.2-Windows-x64/../../escape.txt','C:/escape.txt','Goodseed-0.1.2-Windows-x64/C:/escape.txt','Goodseed-0.1.2-Windows-x64/.. /escape.txt']:
   archive,name=self.archive([(unsafe,b'bad')])
   with self.assertRaises(ValueError):u.extract_verified(archive,self.root/'stage',name)
  self.assertFalse((self.root.parent/'escape.txt').exists())
 def test_symlink_and_incomplete_packages_rejected(self):
  archive,name=self.archive()
  with zipfile.ZipFile(archive,'a') as z:
   info=zipfile.ZipInfo(name+'/link');info.external_attr=(stat.S_IFLNK|0o777)<<16;z.writestr(info,'outside')
  with self.assertRaises(ValueError):u.extract_verified(archive,self.root/'stage',name)
  with zipfile.ZipFile(archive,'w') as z:z.writestr(name+'/readme.txt','incomplete')
  with self.assertRaises(ValueError):u.extract_verified(archive,self.root/'stage2',name)
 def test_existing_target_is_not_overwritten(self):
  archive,name=self.archive();existing=self.root/name;existing.mkdir();(existing/'user.txt').write_text('keep')
  target=u.install_archive(archive,self.root,name,{'tag_name':'v0.1.2-preview.1'})
  self.assertNotEqual(target,existing);self.assertEqual((existing/'user.txt').read_text(),'keep')

 def test_hash_mismatch_never_installs(self):
  install=self.root/'Goodseed-0.1.1-Windows-x64';install.mkdir()
  (install/'release-info.json').write_text(json.dumps({'tag':'v0.1.1-preview.1'}))
  filename='Goodseed-0.1.2-Windows-x64.zip'
  release={'tag_name':'v0.1.2-preview.1','prerelease':True,'assets':[{'name':'SHA256SUMS.txt','browser_download_url':u.PREFIX+'test/SHA256SUMS.txt'},{'name':filename,'browser_download_url':u.PREFIX+'test/'+filename}]}
  def fake_download(url,dest,limit=u.MAX_BYTES):
   if dest.name=='SHA256SUMS.txt':dest.write_text('0'*64+'  '+filename);return 'unused'
   dest.write_bytes(b'tampered');return hashlib.sha256(b'tampered').hexdigest()
  with mock.patch.object(u,'open_url',return_value=io.BytesIO(json.dumps([release]).encode())),mock.patch.object(u,'download',side_effect=fake_download),mock.patch.object(u,'install_archive') as apply:
   with self.assertRaisesRegex(ValueError,'SHA-256 mismatch'):
    u.run(SimpleNamespace(install_dir=str(install),current_version='0.1.1',preview=True,check=False))
   apply.assert_not_called()
  self.assertFalse(any(p.name.startswith('.gsd-download-') for p in self.root.iterdir()))

if __name__=='__main__':unittest.main()
