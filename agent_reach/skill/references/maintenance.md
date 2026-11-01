# 관리

설치·갱신·삭제 요청 시 읽습니다. 포크: https://github.com/ppiljjonku-hash/Agent-Reach

- `doctor`: 로컬 상태와 설치 버전 조회.
- `setup`: 기본 YouTube 채널과 스킬 준비.
- `add twitter`, `add reddit`: 선택 채널의 의존성 준비. 다운로드 전에 사용자 승인을 확인.
- `remove CHANNEL`: 해당 채널과 전용 데이터 제거. 사용자가 만든 파일은 유지.
- `update`: 추가된 채널의 도구와 스킬만 갱신. 프로그램 자체 원격 조회·다운로드 없음.
- 프로그램 갱신: 검토한 포크 체크아웃을 수동 재설치.
- `check CHANNEL --search`: 실제 사이트에서 검색 검사. 로컬 상태 조회와 구분.
- `skill link PATH`: 다른 에이전트의 스킬 경로 연결.
- `uninstall --dry-run`: 삭제 목록을 먼저 보여주고 승인 후 `uninstall`.

OpenCLI 신규 설치와 확장은 테스트 버전 `1.8.7` / `v1.8.7`에 고정됩니다.
키·쿠키·세션 파일·개인 검색 내역을 보고나 이슈에 포함하지 않습니다.
