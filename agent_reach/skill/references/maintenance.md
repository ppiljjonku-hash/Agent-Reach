# 관리

설치·갱신·삭제 요청 시 읽습니다. 설치 소스: https://github.com/ppiljjonku-hash/Agent-Reach/tree/fork-v1

- `doctor`: 로컬 상태와 설치 버전 조회.
- `setup`: 기본 YouTube 채널과 스킬 준비.
- `add twitter`, `add reddit`: 선택 채널의 의존성 준비. 다운로드 전에 사용자 승인을 확인.
- `remove CHANNEL`: 해당 채널과 전용 데이터 제거. 사용자가 만든 파일은 유지.
- `update`: 추가된 채널의 도구와 스킬만 갱신. 프로그램 자체 원격 조회·다운로드 없음.
- 프로그램 갱신: 검토한 포크 체크아웃을 수동 재설치.
- `check CHANNEL --search`: 실제 사이트에서 검색 검사. 로컬 상태 조회와 구분.
- `skill link PATH`: 다른 에이전트의 스킬 경로 연결.
- `uninstall --dry-run`: 삭제 목록을 먼저 보여주고 승인 후 `uninstall`.

Node·npm·ffmpeg·시스템 Google Chrome은 사용자가 미리 설치합니다. 사용할 경우 uv도 미리 설치합니다.
누락 시 `NEED_SETUP` 설치 안내를 보고합니다. 런타임·브라우저 자동 다운로드로 우회하지 않습니다.
macOS Chrome은 엄격한 서명 검사와 Google 팀 `EQHXZ8M8AV` 확인 후 실행합니다.
Linux·Windows는 서명 확인 없음.
OpenCLI `1.8.7` tgz SHA-512와 확장 `1.0.23` zip SHA-256 검증이 필수입니다.
npm 훅은 비활성입니다. 전이 의존성 전체 해시 고정은 아닙니다.
출처·통신 목록과 설치 훅 생략 영향은 `docs/install.md`를 확인합니다.
키·쿠키·세션 파일·개인 검색 내역을 보고나 이슈에 포함하지 않습니다.
