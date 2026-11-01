from __future__ import annotations

from urllib.parse import urlsplit


def domain_matches(host: str, *domains: str) -> bool:
    normalized_host = str(host or "").lower().lstrip(".").rstrip(".")
    if not normalized_host:
        return False
    for domain in domains:
        allowed = domain.lower().lstrip(".").rstrip(".")
        if normalized_host == allowed or normalized_host.endswith("." + allowed):
            return True
    return False


def host_matches(url: str, *domains: str) -> bool:
    try:
        parsed = urlsplit(url)
        host = (parsed.hostname or "").lower().rstrip(".")
        _ = parsed.port
    except (TypeError, ValueError):
        return False
    if parsed.scheme.lower() not in {"http", "https"}:
        return False
    if not host or parsed.username is not None or parsed.password is not None:
        return False
    return domain_matches(host, *domains)
