# 설치

대상 소스는 https://github.com/ppiljjonku-hash/Agent-Reach/tree/fork-v1 입니다.
PyPI의 동명 패키지가 아니라 `fork-v1` 태그 체크아웃에서 설치합니다.
`fork-v1`은 이번 변경 병합 후 생성할 릴리스 태그입니다. 태그가 없으면 설치를 중단합니다.

```bash
git clone --branch fork-v1 --depth 1 https://github.com/ppiljjonku-hash/Agent-Reach.git
cd Agent-Reach
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

X·Reddit은 OpenCLI와 시스템 Google Chrome의 전용 로컬 프로필을 사용합니다.
Node.js·npm·npx, ffmpeg, 사용할 경우 uv·uvx는 사용자가 미리 설치합니다.
macOS 예: `brew install node ffmpeg`, uv가 필요하면 `brew install uv`.
Chrome은 https://www.google.com/chrome/ 또는 `brew install --cask google-chrome`으로 설치합니다.
누락된 도구는 설치 안내와 `NEED_SETUP`으로 실패하며 Reach가 자동 다운로드하지 않습니다.
검색어·콘텐츠 URL을 별도의 검색 서비스로 전송하지 않습니다.
사이트에서 인증을 요구할 때만 사용자가 직접 `agent-reach login twitter` 또는
`agent-reach login reddit`으로 로그인합니다. 에이전트가 대신 로그인하지 않습니다.

YouTube 자막에는 전사 키가 필요하지 않습니다. 음성 전사가 필요한 경우에만
`agent-reach configure groq-key` 또는 `agent-reach configure openai-key`의 숨김 입력으로
키를 설정합니다. 전사 실행 시 오디오가 해당 API에 업로드됩니다.

## 실행 파일과 아티팩트 출처

브라우저는 시스템 Google Chrome만 사용합니다. macOS에서는 실행 전 앱 번들에
`codesign --verify --deep`(정상 설치본도 Finder xattr 때문에 `--strict`를 통과하지 못해 빼고, 대신 요구식으로 고정)에 식별자 `com.google.Chrome`, Apple 신뢰 체인,
서명자 `EQHXZ8M8AV`(Google LLC) 요구식을 적용해 성공할 때만 실행합니다.
`/Applications/` 또는 `~/Applications/` 아래의 표준 Chrome 실행 경로만 허용하며,
경로의 심볼릭 링크와 실행 직전 재검증에서 실행 파일 inode 변경을 거부합니다.
검사 오류·시간 초과·다른 서명은 `NEED_SETUP`으로 실행을 거부합니다.
Linux·Windows는 서명 확인 없음. Chrome 설치·갱신은 사용자가 관리합니다.

OpenCLI 신규 설치·재설치는 다음 tgz를 받아 SHA-512를 직접 검증한 다음
기존 npm prefix에 로컬 tgz로 `npm install --ignore-scripts --no-fund --no-audit`를 실행합니다.
확장은 다음 zip의 SHA-256 검증 후에만 풀며 기록된 해시가 일치할 때만 기존 폴더를 재사용합니다.
해시 불일치는 아카이브를 삭제하고 실패합니다.
Reach가 직접 다운로드하고 고정 해시로 검증하는 아티팩트는 이 두 개이며, npm 전이 의존성 다운로드는 별도(해시 고정 없음)입니다.

| 아티팩트 | 고정 URL | 고정 해시 |
|---|---|---|
| OpenCLI 1.8.7 | `https://registry.npmjs.org/@jackwener/opencli/-/opencli-1.8.7.tgz` | `sha512-2M+oPc70R1jNGzKzNrsm3fN4/gdvxCKlla7s9eaaTjkDjlzHpoZFN1YdV01A185kwCTN/ChOg+rbO4epO73c3w==` |
| 확장 1.0.23 | `https://github.com/jackwener/OpenCLI/releases/download/v1.8.7/opencli-extension-v1.0.23.zip` | SHA-256 `e3399db1e9dd626519a8719d638d3c3813494d1f030c1e96799e05ebe7ba5340` |

제한: OpenCLI의 의존 패키지는 npm 설정의 레지스트리에서 해석됩니다.
전이 의존성 전체의 해시를 이 포크가 고정하지 않으므로 재현 가능한 전체 공급망은 아닙니다.
기존 사용자 OpenCLI는 호환 버전이면 그대로 사용하며 그 설치 출처를 소급 검증하지 않습니다.
Windows는 시스템 Chrome 정책상 확장을 Web Store에서 사용자가 설치합니다.
이 수동 Web Store 경로에는 위 zip 해시 고정이 적용되지 않습니다.

## 설치 훅 생략 영향

읽기 전용으로 확인한 upstream 커밋은 `87b60a36590c3e2a466c37266c3348d73d7f68fe`입니다.
[`scripts/postinstall.js`](https://github.com/jackwener/opencli/blob/87b60a36590c3e2a466c37266c3348d73d7f68fe/scripts/postinstall.js)는
셸 자동완성, Spotify 템플릿, 확장 설치 안내를 생성합니다. 생략해도 X·Reddit 추출에는 필요하지 않습니다.
[`scripts/fetch-adapters.js`](https://github.com/jackwener/opencli/blob/87b60a36590c3e2a466c37266c3348d73d7f68fe/scripts/fetch-adapters.js)는
네트워크 다운로드 없이 패키지 번들 해시를 기준으로 `~/.opencli/clis/`의 오래된 override·shim을
삭제하고 manifest를 기록합니다. 번들 어댑터는 이미 패키지에 있으므로 대체 다운로드는 필요 없습니다.
훅을 끄면 사용자 override 자동 정리도 생략됩니다. 이전 override가 있으면 사용자가 내용을 검토하고
직접 정리해야 하며 Reach는 사용자 설정을 삭제하지 않습니다.

## 남는 다운로드와 통신

| 목적지 | 시점·용도 | 해시 고정 |
|---|---|---|
| 위 npm tgz URL | OpenCLI 미설치 시 `add`·명시적 도구 갱신/재설치 | SHA-512 고정 |
| npm 설정 레지스트리(기본 `registry.npmjs.org`) 및 해석된 의존성 URL | npm이 전이 의존성을 해석·다운로드 | 포크의 전체 해시 고정 없음, 설치 훅 비활성 |
| 위 GitHub zip URL, GitHub 릴리스 CDN 리다이렉트 | 확장 최초 준비·고정 해시 기록이 없는 설치·명시적 갱신 | 최종 zip SHA-256 고정, 릴리스 API 조회 없음 |
| `chromewebstore.google.com`, Google 확장 배포 서버 | Windows 사용자 수동 확장 설치·Chrome 관리 갱신 | Reach의 해시 고정 없음 |
| `x.com`, `reddit.com` 및 해당 사이트 API·미디어·인증 호스트 | OpenCLI 검색·읽기·로그인·실제 `check` | 콘텐츠 통신, 해시 고정 대상 아님 |
| `youtube.com`, YouTube API·자막·`googlevideo.com` 등 미디어 호스트 | yt-dlp 검색·정보·자막·전사용 오디오 다운로드 | 콘텐츠 통신, 해시 고정 대상 아님 |
| `api.groq.com/openai/v1/audio/transcriptions`, `api.openai.com/v1/audio/transcriptions` | 키 설정 후 명시적 음성 전사 | 오디오 업로드, 해시 고정 대상 아님 |
| `127.0.0.1:<browser-port>`(기본 9222), `127.0.0.1:19825` | CDP·OpenCLI Bridge의 로컬 HTTP/WebSocket | 외부 통신 아님 |
| GitHub 포크 `fork-v1`, pip 설정 인덱스(기본 PyPI 및 파일 CDN) | 사용자가 승인한 최초 설치·수동 프로그램 재설치 | 소스 태그·constraints 버전 고정, pip 의존성 전체 해시 고정 없음 |

프록시를 설정하면 위 트래픽은 해당 프록시를 경유할 수 있습니다.
Chrome 자체 서비스·자동 갱신 및 npm 사용자 설정은 별도 신뢰 경계입니다.
Reach는 Node·uv 설치 스크립트, 브라우저 바이너리, 릴리스 메타데이터를 자동으로 받지 않습니다.

갱신은 [update.md](update.md), 세션은 [sessions.md](../agent_reach/skill/references/sessions.md)를 참고합니다.
