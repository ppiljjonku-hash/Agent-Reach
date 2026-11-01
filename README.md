# Agent Reach

X·Reddit·YouTube만 사용하는 개인 포크입니다.
저장소: https://github.com/ppiljjonku-hash/Agent-Reach

## 지원 채널

| 채널 | 기능 | 로컬 도구 | 조건 |
|---|---|---|---|
| twitter | 검색, 프로필, 타임라인, 답글 | OpenCLI | 사이트가 요구하면 사용자 로그인 |
| reddit | 검색, 게시물·상위 댓글, 서브레딧 | OpenCLI | 사이트가 요구하면 사용자 로그인 |
| youtube | 검색, 영상 정보, 자막, 음성 전사 | yt-dlp, ffmpeg | 전사는 사용자가 설정한 Groq/OpenAI 키 필요 |

```bash
agent-reach channels
agent-reach twitter search "python" --limit 5
agent-reach reddit search "python" --limit 5
agent-reach youtube search "python" --limit 5
agent-reach read https://www.youtube.com/watch?v=jNQXAC9IVRw
```

## 설치와 관리

[설치](docs/install.md) · [수동 갱신](docs/update.md) · [문제 해결](docs/troubleshooting.md)

PyPI의 같은 이름 패키지는 이 프로젝트가 아닙니다.
[포크 `fork-v1`](https://github.com/ppiljjonku-hash/Agent-Reach/tree/fork-v1) 태그에서 설치하세요.
태그는 이번 변경 병합 후 생성됩니다. 태그가 없으면 설치를 중단하세요.
`setup`은 기본 YouTube 채널과 스킬을 준비합니다. `add twitter`와 `add reddit`은
선택한 채널의 OpenCLI와 확장을 준비합니다. Node·npm·ffmpeg 및 Google Chrome은 미리 설치해야 합니다.
누락 시 `NEED_SETUP`과 설치 안내를 반환하며 자동으로 받지 않습니다.
`doctor`는 로컬 상태 조회이고 `check`는 실제 사이트에 요청하는 검사입니다.
`update`는 채널 도구와 스킬만 갱신하며 프로그램 자체는 내려받지 않습니다.

## 개인정보와 보안

- 검색어와 URL을 별도의 검색·크롤링 서비스로 보내는 우회 경로가 없습니다.
- X·Reddit은 로컬 OpenCLI와 전용 브라우저, YouTube는 로컬 yt-dlp를 사용합니다.
  실제 콘텐츠 요청은 해당 사이트와 사이트가 사용하는 미디어 호스트에 전송됩니다.
- 음성 전사는 예외입니다. 사용자가 키를 설정하고 `youtube transcribe`를 실행하면
  오디오를 선택된 Groq/OpenAI API에 보냅니다. 키가 없으면 전사 전에 실패합니다.
- CDP는 `127.0.0.1`에 바인딩합니다. 세션 복사는 연결된 로컬 브라우저 사이에서
  요청한 사이트의 쿠키만 복사합니다. 원본 브라우저와 암호 저장소는 변경하지 않습니다.
- 전용 프로필과 세션은 `~/.agent-reach/`에 보관합니다. 같은 컴퓨터의 다른 프로세스와
  설치한 브라우저 확장은 신뢰 경계 안에 있으므로 전용 계정 사용을 권장합니다.
- 시스템 Google Chrome만 실행합니다. macOS는 실행 전 엄격한 `codesign` 검사와 Google 팀
  `EQHXZ8M8AV` 확인이 필수입니다. Linux·Windows는 서명 확인 없음.
- OpenCLI `1.8.7` tgz는 SHA-512, 확장 `1.0.23` zip은 SHA-256 검증 후 사용합니다.
  npm 설치 훅은 실행하지 않습니다. 전이 의존성은 레지스트리에서 해석되며 전체 해시는 고정하지 않습니다.
  기존 사용자 OpenCLI와 Windows 수동 Web Store 설치에는 이 해시 검증이 적용되지 않습니다.
  브라우저 확장은 로그인 세션에 접근할 수 있습니다. [출처·통신·훅 생략 범위](docs/install.md)를 확인하세요.
- API 키는 채팅이나 명령 인자 대신 `agent-reach configure groq-key`의 숨김 입력으로 설정합니다.
- 로그·오류·결과를 공유하기 전 개인정보를 확인하세요. 세션 파일은 공유하지 마세요.

## 개발 검증

```bash
python -m pip install -c constraints.txt -e '.[dev]'
python -m pytest -q
python -m agent_reach.cli channels
```

실계정 검증 기록은 `scripts/record_release_acceptance.py`로 따로 생성합니다.
현재 포크는 실계정 검증을 완료하지 않았으며 릴리스 게이트도 통과 처리하지 않습니다.

## 라이선스

[MIT](LICENSE). 기존 저작권 고지를 유지합니다.
