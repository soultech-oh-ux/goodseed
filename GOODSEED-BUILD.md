# Goodseed 소스 빌드

기준 저장소: https://github.com/idoforgod/cys-terminal
기준 커밋: 8d71882e5cb293dabcb0fb668aee0267fc4a995e
Goodseed 로컬판: 0.1.0

원본 LICENSE를 보존합니다. UI 추가 파일은 ui/src/goodseed.ts와 goodseed.css입니다.

Windows 일반 빌드에는 Rust, Microsoft C++ Build Tools와 Windows SDK, Node.js, Git이 필요합니다. 원본 프로젝트도 Tauri 2를 사용합니다. 이 PC에서 생성한 바이너리는 별도 GNU Rust/LLVM-MinGW 도구 체인으로 빌드했습니다.

ZIP에는 빌드 캐시·개인 설정·원본 설치 폴더의 데이터베이스·계정 토큰을 넣지 않습니다. runtime과 resources/binaries는 배포 폴더에 있습니다.

1. 소스 ZIP을 풀고 git init 후 git add . 로 파일을 추적합니다. 원본 build.rs는 git ls-files gsdjavis-pack을 기준으로 임베드 파일을 결정하므로 git 인덱스가 필요합니다.
2. ui 폴더에서 npm install을 실행합니다.
3. esbuild로 ui/src/main.ts를 browser 번들로 묶어 ui/dist/main.js를 생성합니다. ui/index.html, ui/src/style.css, ui/src/goodseed.css 및 xterm.css도 ui/dist에 복사합니다. buildGoodseed.ps1을 참고하세요.
4. 프로젝트 루트에서 cargo build --release --bins 로 gsd.exe와 gsdd.exe를 만듭니다.
5. 배포 폴더의 pack.tar.gz, pack-manifest.json, runtime을 src-tauri/resources 및 src-tauri/runtime에 배치합니다. 팩을 바꿨다면 원본 scripts/bundle-prep.sh의 manifest 기반 동일성 검증·결정론 tar 절차를 다시 수행해야 합니다.
6. gsd.exe/gsdd.exe를 src-tauri/binaries/gsd-<Rust host triple>.exe 및 gsdd-<Rust host triple>.exe로 복사합니다.
7. cargo build --release -p gsd-app 으로 GUI를 빌드합니다. GNU 타깃에서는 webview2-com-sys 패키지의 x64/WebView2Loader.dll을 실행 파일 옆에 배치합니다.
8. gsd-app.exe를 Goodseed.exe로 복사하고 CLI·데몬·런타임·팩을 같은 폴더로 묶습니다.

검증: UI 104개 테스트와 Goodseed 화면 통합 9개는 통과했습니다. Rust 전체 테스트는 통과하지 않았습니다. evidence의 결과와 실패 로그를 참고하고 실제 Windows 세션에서 검증 후 배포 범위를 넓히세요. 원본의 Pro 라이선스·서명 검증 로직은 유지합니다.
