---
name: agent-reach
description: Search X, Reddit or YouTube and read supported links using local site tools. Use for these sites, session management and CLI errors.
metadata:
  homepage: https://github.com/ppiljjonku-hash/Agent-Reach
  version: "{{VERSION}}"
---

# Agent Reach

Run `agent-reach channels` for actions and parameters, then `agent-reach CHANNEL ACTION`.
Read the single JSON object's `ok`, `items` and `error.code`. Report only content actually returned.
Installation and doctor status are not live acceptance.

```bash
agent-reach twitter search "python" --limit 5
agent-reach reddit search "python" --limit 5
agent-reach youtube search "python" --limit 5
```

## Channels

{{CHANNEL_TABLE}}

Only local site tools are used. Unsupported URLs are rejected. Queries and URLs are not forwarded
to separate search or crawling services. Audio transcription is a separate, explicit upload to
Groq/OpenAI requiring a user-configured key. Use hidden `configure groq-key` or `configure openai-key` prompts.

Read [Sessions](references/sessions.md) for login, logout, account selection or `NEED_LOGIN`.
Reuse only site-scoped local cookies; users perform their own login. Never request passwords or cookies in chat.
Stop on `PLATFORM_BLOCKED`; wait on `RATE_LIMITED`. Do not switch profiles or external services to bypass errors.
Read [Maintenance](references/maintenance.md) for setup, update or uninstall requests.
Read [Capabilities](references/capabilities.md) for supported operations and result completeness.
Program self-update and remote version checks are not provided.
