# 자연어 제작과 사용자 맞춤 기능 학습

`gsd ask`는 설치·로그인된 Codex CLI로 자연어 요청을 실행한다. 기존 터미널에서 사용할 수 있고 데몬 연결은 필요 없다. Python은 배포본의 동봉 런타임을 사용한다. 소스 실행 시에는 Python 3와 Codex CLI가 필요하다. 모델 사용에는 연결한 Codex 계정의 사용량이 적용된다.

```powershell
gsd ask "초보자인데 할 일 관리 앱을 만들어줘. 저장과 검색도 넣어줘"
gsd ask --cwd "C:\work\todo" "검색이 느려. 원인을 고치고 테스트해줘"
gsd ask --level advanced "CSV 가져오기 기능을 추가해줘"
gsd ask --preview "입력 폼 검증 기능을 만들어줘"
```

기본 작업 폴더는 `gsd workspace-dir`과 같다. `--cwd`로 프로젝트를 지정할 수 있다. 기존 코드를 읽고, 요청 범위의 기능을 구현하고, 오류를 수정하며 테스트한다. `--preview`는 프롬프트와 재사용할 절차만 출력한다. 실제 AI 실행은 하지 않는다. 기본 실행 제한은 1800초이고 `--timeout 3600` 등으로 최대 7200초까지 지정한다. 중단·시간초과 시 프로젝트 변경은 남을 수 있으므로 결과 파일을 확인한다. 자동 복원을 가장하지 않는다.

## 사용할수록 개선되는 부분

학습은 기본으로 켜져 있다. 완료된 작업에서 유용한 절차를 최대 5개 제안받고, 제안의 검증 명령과 실제 Codex 명령 실행 로그(종료코드 0)가 일치할 때만 저장한다. 실패·미완료·시간초과·잘못된 결과에는 새 절차를 적용하지 않는다. 실제 명령 실행 근거를 대조하는 것으로, 테스트의 충분성이나 앱 전체의 무결함을 보장하는 것은 아니다.

다음 요청에서는 같은 프로젝트의 관련 절차를 최대 8개 검색해 참고하도록 전달한다. 기존 코드를 확인해 절차를 수정하고, 같은 이름으로 개선한 절차는 새 버전으로 저장한다. 현재 요청과 프로젝트 규칙이 우선한다. 작업 폴더가 다르면 절차를 자동 공유하지 않는다. 기능이 필요하지 않거나 검증 근거가 없으면 새 버전을 만들지 않는다.

이것은 모델 가중치 재훈련이나 gsd 실행파일의 자가 교체가 아니다. 실제 앱 기능은 프로젝트 코드에 추가되고, 반복 작업 능력은 버전 관리되는 재사용 절차로 확장된다. 제품 릴리스 설치·검증은 기존 `gsd update`가 담당한다. 기존 일반 셸 명령과 `gsd send`를 가로채지 않으며, 자연어 작업에는 `gsd ask`를 사용한다.

## 수준과 학습 관리

```powershell
gsd learn profile --level beginner
gsd learn profile --level intermediate
gsd learn profile --level advanced
gsd learn status
gsd learn history
gsd learn rollback form-validation --version 1
gsd learn forget form-validation
gsd learn off
gsd learn on
gsd ask --no-learn "이번 요청에는 학습 절차를 사용하거나 저장하지 마"
gsd learn status --cwd "C:\work\todo"
```

기본 수준은 `beginner`다. `profile`은 사용자 전역 수준을 저장하며 `ask --level`은 해당 요청에만 적용된다. 요청에 “초보자인데”, “쉽게 설명”, “전문가 수준으로”, “중급 수준으로”처럼 명시적인 피드백이 있으면 해당 수준으로 설명하고 완료 후 저장한다. 작업 횟수나 전문 용어만으로 사용자 수준을 임의로 높이지 않는다. 학습 끄기 또는 `--no-learn`은 절차 재사용·절차 저장·피드백 수준 저장을 모두 끈다. 실행 도중 학습을 꺼도 새 절차를 저장하지 않는다.

`rollback`은 과거 절차를 새 버전으로 복원하여 이력을 보존한다. `forget`은 해당 프로젝트에서 지정한 절차의 모든 버전을 삭제한다. 프로젝트 소스의 변경을 되돌리는 명령은 아니다.

기존 데몬 기반 RSI 인터페이스인 `gsd learn "학습 주제"`와 `gsd learn --status`도 유지한다. 새 로컬 학습 상태는 `gsd learn status`로 조회한다.

설정·절차·검증 명령·실행 상태는 `~/.goodseed/state/assistant/assistant.sqlite3`에 저장된다. 원문 프롬프트와 전체 응답은 이 DB에 저장하지 않는다. 절차·검증 명령에는 모델이 프로젝트 정보를 포함할 수 있으므로 `learn status/history`에서 검토하고 `forget`으로 제거할 수 있다. AI 실행에는 현재 요청, 작업 폴더, 관련 절차가 연결된 Codex 모델로 전달되며 프로젝트 도구 접근은 Codex 설정을 따른다. 자동 실행은 `workspace-write` 샌드박스를 사용하고 권한 우회 옵션을 추가하지 않는다. 테스트용 별도 저장소는 `GSD_ASSISTANT_HOME`으로 지정할 수 있다.
