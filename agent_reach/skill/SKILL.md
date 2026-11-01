---
name: agent-reach
description: X·Reddit·YouTube 링크를 읽거나 해당 사이트를 검색할 때 사용하는 로컬 CLI. 지원 액션 확인, 세션 관리, 오류 처리를 제공한다.
metadata:
  homepage: https://github.com/ppiljjonku-hash/Agent-Reach
  version: "{{VERSION}}"
---

# Agent Reach

## 실행

1. `agent-reach channels`로 지원 액션과 인자를 확인한다.
2. `agent-reach CHANNEL ACTION`을 실행하고 단일 JSON의 `ok`, `items`, `error.code`를 읽는다.
3. 실제 반환된 범위만 보고한다. 설치나 doctor 상태를 실계정 검증 성공으로 표현하지 않는다.

```bash
agent-reach twitter search "python" --limit 5
agent-reach reddit search "python" --limit 5
agent-reach youtube search "python" --limit 5
agent-reach read https://www.youtube.com/watch?v=jNQXAC9IVRw
```

## 채널

{{CHANNEL_TABLE}}

검색과 읽기는 해당 사이트의 로컬 도구만 사용한다. 지원하지 않는 일반 URL은 거절한다.
사용자 요청·검색어·URL을 별도의 검색·크롤링 서비스로 보내지 않는다.

## 인증과 개인정보

X·Reddit은 전용 로컬 브라우저를 사용한다. 기존 연결 브라우저에서 요청한 사이트 쿠키만
복사할 수 있다. 로그인·계정 변경·`NEED_LOGIN`이면 [세션](references/sessions.md)을 읽는다.
로그인이 실제 필요한 경우 사용자 본인이 수행한다. 비밀번호나 쿠키를 채팅으로 요청하지 않는다.
Groq/OpenAI 전사는 오디오 외부 업로드다. 사용자 요청과 설정된 키가 있을 때만 실행한다.
키는 `configure groq-key` 또는 `configure openai-key`의 숨김 입력으로 설정한다.

## 오류와 관리

`RATE_LIMITED`는 대기하고 `PLATFORM_BLOCKED`는 중단한다. 다른 프로필·외부 서비스로 우회하지 않는다.
`NEED_SETUP`은 doctor의 구체적 원인을 확인한다. 재시도 루프를 만들지 않는다.
설치·갱신·삭제 요청이면 [관리](references/maintenance.md)를 읽는다.
지원 범위와 댓글·자막 완전성 질문이면 [능력 범위](references/capabilities.md)를 읽는다.
프로그램 자체 갱신이나 원격 버전 조회는 제공하지 않는다.
