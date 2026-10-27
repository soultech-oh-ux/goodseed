# Goodseed Terminal

Windows AI 작업 공간 · 오경근 박사 · 0.1.0 시험판

터미널, 분할 작업 공간, AI 세션과 작업 현황을 한 화면에서 관리합니다.

## 추가한 기능

- 한국어 시작 안내와 단축키 도움말
- 화면 상단 명령 검색 버튼
- 사이드바와 관리 패널을 숨기는 집중 모드
- 별도 프로필·상태·통신 경로
- TypeScript 타입 오류 및 명령 팔레트 실패 처리 개선

## 현재 상태

Windows x64 실행 파일을 빌드했습니다. 안정판으로 검증한 상태는 아닙니다.

| 검사 | 결과 |
|---|---|
| UI 테스트 | 104 통과 |
| Goodseed 화면 통합 검사 | 9 통과, 네이티브 호출은 테스트 콜백 사용 |
| TypeScript 검사 | 통과 |
| Rust 통신 경로 관련 검사 | 4 통과 |
| Rust 라이브러리 전체 검사 | 111 통과 / 16 실패 |
| 데몬 검사 재실행 | 316 통과 / 62 실패 / 장시간 실행 테스트 1개 제외 |
| 실제 데스크톱 연결 | 현재 실행 환경에서 named pipe 접근 거부로 완료하지 못함 |

실패 원인에는 Windows 경로·테스트 격리·소스에 없는 fixture 등이 포함됩니다. 테스트 문제와 실제 제품 문제를 분리해 확인해야 합니다. AI CLI 설치·계정 로그인은 별도입니다.

## 개발

`ui` 폴더에서 `npm ci`, `npm run typecheck`, `npm run build`를 실행합니다. Bun 설치 후 `bun test ./src`로 UI 테스트를 실행합니다.

네이티브 빌드와 실행 조건은 [GOODSEED-BUILD.md](GOODSEED-BUILD.md)를 참고하세요.

향후 작업은 [ROADMAP.md](ROADMAP.md), 변경 기록은 [CHANGELOG.md](CHANGELOG.md)에 관리합니다.

## 라이선스

[LICENSE](LICENSE)의 MIT 저작권 고지와 [NOTICE.md](NOTICE.md)의 출처 정보를 유지합니다.

