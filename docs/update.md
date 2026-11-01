# 수동 갱신

프로그램 자체 갱신과 원격 버전 확인은 제거했습니다. 검토한
https://github.com/ppiljjonku-hash/Agent-Reach 소스를 [설치 절차](install.md)로 다시 설치합니다.
`agent-reach update`는 추가된 채널의 도구와 스킬만 갱신합니다.
OpenCLI는 테스트 버전 `1.8.7`, 확장은 `v1.8.7` 릴리스에 고정되어 있습니다.
갱신에는 도구 다운로드가 필요합니다. 실행 전에 사용자 승인을 받습니다.
`agent-reach doctor`로 상태를 확인하고 실제 사이트 검사는 `agent-reach check CHANNEL`로 별도 수행합니다.
