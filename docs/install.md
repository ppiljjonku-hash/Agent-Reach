# 설치

대상 저장소는 https://github.com/ppiljjonku-hash/Agent-Reach 입니다.
PyPI의 동명 패키지가 아니라 검토한 포크 체크아웃에서 설치합니다.

```bash
python -m pip install -c constraints.txt .
agent-reach channels
agent-reach setup --text
```

Python 3.10 이상이 필요합니다. 설치 전 의존성 다운로드와 로컬 도구 설치에 대한
사용자 승인을 확인합니다. `setup`의 결과를 보고하고 실패를 숨기지 않습니다.
기본 채널은 YouTube이며 필요할 때만 다음을 실행합니다.

```bash
agent-reach add twitter
agent-reach add reddit
```

X·Reddit은 OpenCLI와 전용 로컬 브라우저를 사용합니다. CloakBrowser는 공유 브라우저
런타임으로 유지됩니다. 설치와 도구 갱신은 패키지 및 브라우저 배포 서버에 접속합니다.
검색어·콘텐츠 URL을 별도의 검색 서비스로 전송하지 않습니다.
사이트에서 인증을 요구할 때만 사용자가 직접 `agent-reach login twitter` 또는
`agent-reach login reddit`으로 로그인합니다. 에이전트가 대신 로그인하지 않습니다.

YouTube 자막에는 전사 키가 필요하지 않습니다. 음성 전사가 필요한 경우에만
`agent-reach configure groq-key` 또는 `agent-reach configure openai-key`의 숨김 입력으로
키를 설정합니다. 전사 실행 시 오디오가 해당 API에 업로드됩니다.

갱신은 [update.md](update.md), 세션은 [sessions.md](../agent_reach/skill/references/sessions.md)를 참고합니다.
