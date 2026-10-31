# Run in ui/ after npm install. Requires esbuild (npm install --no-save esbuild).
$ErrorActionPreference='Stop'
& npx.cmd --no-install esbuild src/main.ts --bundle --outdir=dist --platform=browser --minify
if($LASTEXITCODE -ne 0){throw 'UI build failed'}
Copy-Item index.html,src/style.css,src/goodseed.css dist/
Copy-Item node_modules/@xterm/xterm/css/xterm.css dist/xterm.css
