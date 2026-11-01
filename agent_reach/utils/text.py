"""Text helpers."""

from __future__ import annotations

import re
from typing import Any

_URL_CREDENTIALS_RE = re.compile(
    r"([A-Za-z][A-Za-z0-9+.\-]{0,19}://)[^/\s@]+@"
)
_BARE_USERINFO_RE = re.compile(
    r"(?<![A-Za-z0-9._%+\-])[^:/\s@]+:[^/\s@]+@(?=[A-Za-z0-9.\-\[])"
)
_URL_QUERY_SECRET_RE = re.compile(
    r"([?&#](?:"
    r"access[_-]?token|refresh[_-]?token|auth[_-]?token|token|ct0|bearer|"
    r"api[_-]?key|key|password|passwd|secret|"
    r"signature|sig|session(?:id)?|cookie|credential"
    r")=)[^&#\s]*",
    re.IGNORECASE,
)
_HEADER_SECRET_RE = re.compile(r"(?im)\b((?:authorization|proxy-authorization|set-cookie|cookie)\s*:\s*)[^\r\n]+")
_SECRET_KEY_RE = re.compile(
    r"^(?:authorization|proxy[_-]?authorization|set[_-]?cookie|cookies?|"
    r"token|bearer|(?:access|refresh|auth)[_-]?token|ct0|(?:groq|openai)[_-]?api[_-]?key|"
    r"api[_-]?key|password|passwd|secret|credentials?|session(?:id)?)$", re.I,
)


def scrub_url_credentials(text: object) -> str:
    """Redact URL userinfo and sensitive query/fragment values from text."""
    scrubbed = _URL_CREDENTIALS_RE.sub(r"\1***@", str(text))
    scrubbed = _BARE_USERINFO_RE.sub("***@", scrubbed)
    scrubbed = _URL_QUERY_SECRET_RE.sub(r"\1***", scrubbed)
    return _HEADER_SECRET_RE.sub(r"\1***", scrubbed)


def scrub_sensitive_data(value: Any) -> Any:
    if isinstance(value, dict):
        cookie = isinstance(value.get("name"), str) and _SECRET_KEY_RE.fullmatch(value["name"])
        return {key: "***" if _SECRET_KEY_RE.fullmatch(str(key)) or (cookie and key == "value")
                else scrub_sensitive_data(item) for key, item in value.items()}
    if isinstance(value, list):
        return [scrub_sensitive_data(item) for item in value]
    if isinstance(value, str):
        return scrub_url_credentials(value)
    return value
