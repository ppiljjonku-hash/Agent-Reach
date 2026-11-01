# 문제 해결

지원 채널은 `twitter`, `reddit`, `youtube`입니다. `agent-reach channels`로 사용법을 확인합니다.
`agent-reach doctor --text`는 로컬 상태만 보여줍니다. 설치 성공은 실계정 검증이 아닙니다.
`agent-reach check CHANNEL --search`는 실제 사이트 요청을 수행합니다.

| 오류 | 조치 |
|---|---|
| BAD_INPUT | 채널·액션·URL·인자를 확인합니다. 일반 웹 URL은 읽지 않습니다. |
| NEED_SETUP | doctor의 의존성 또는 키 안내를 확인합니다. |
| NEED_LOGIN | 로컬 세션을 확인한 뒤 필요하면 사용자가 직접 로그인합니다. |
| RATE_LIMITED | 지정된 대기 시간을 지킵니다. 우회 재시도하지 않습니다. |
| PLATFORM_BLOCKED | 자동화를 중단하고 공식 사이트에서 사용자가 확인합니다. |
| TIMEOUT / UPSTREAM_BROKEN | 실패한 도구와 단계를 확인합니다. 외부 검색으로 우회하지 않습니다. |
| NOT_FOUND | 링크와 콘텐츠 ID를 확인합니다. |
| BUSY | 같은 브라우저를 사용하는 작업이 끝날 때까지 기다립니다. |

## 브라우저와 세션

`browser status`, `browser profiles`는 상태 조회입니다.
`browser use ID`는 기존 연결된 로컬 로그인 출처를 선택합니다.
`login CHANNEL --import-existing`은 사이트별 로컬 쿠키를 다시 복사합니다.
`login CHANNEL`은 사용자가 로그인할 전용 창을 엽니다.
`logout CHANNEL`은 해당 사이트의 전용 세션만 제거합니다.
CDP 포트를 외부에 노출하거나 임의 원격 주소를 연결하지 마세요.
세션 세부 사항은 [세션 문서](../agent_reach/skill/references/sessions.md)를 참고합니다.

## 전사

Groq/OpenAI 키가 없으면 전사는 실패합니다. 자막은 전사와 별개입니다.
전사는 오디오 외부 업로드이므로 사용자 동의와 키 설정 후에만 실행합니다.

## 신고

https://github.com/ppiljjonku-hash/Agent-Reach/issues
오류 보고에 쿠키, 세션 파일, API 키, 검색 내역, 개인정보를 첨부하지 마세요.
