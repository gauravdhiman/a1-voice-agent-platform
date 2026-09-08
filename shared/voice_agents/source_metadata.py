"""Canonical call-source metadata and URL normalization helpers."""

from __future__ import annotations

from typing import Optional
from urllib.parse import urlsplit, urlunsplit

MAX_SOURCE_DOMAIN_LENGTH = 255
MAX_SOURCE_URL_LENGTH = 2048

CALL_SOURCE_TYPES = frozenset(
    {
        "phone",
        "web_test",
        "web_embed",
        "web_demo",
        "web_public",
    }
)

_SOURCE_TYPE_BY_PURPOSE = {
    "phone": "phone",
    "test_call": "web_test",
    "embed": "web_embed",
    "public": "web_public",
}


def source_type_for_purpose(purpose: str) -> Optional[str]:
    """Return the stable call-log source type for a session purpose."""
    return _SOURCE_TYPE_BY_PURPOSE.get(purpose)


def normalize_domain(value: Optional[str]) -> Optional[str]:
    """Return a safe, lower-case hostname from an origin or domain value.

    Schemes, paths, ports, and a leading ``www.`` are ignored so the result
    can be used for domain allowlist comparisons. Values containing user
    credentials, malformed ports, or no hostname are rejected.
    """
    if not isinstance(value, str):
        return None

    candidate = value.strip()
    if not candidate:
        return None
    if candidate.lower() == "null":
        return None
    if "://" not in candidate:
        candidate = f"//{candidate}"

    try:
        parsed = urlsplit(candidate)
        if parsed.username is not None or parsed.password is not None:
            return None
        # Accessing port validates malformed numeric ports.
        _ = parsed.port
        hostname = parsed.hostname
    except ValueError:
        return None

    if not hostname:
        return None

    hostname = hostname.rstrip(".").lower()
    if hostname.startswith("www."):
        hostname = hostname[4:]
    try:
        hostname = hostname.encode("idna").decode("ascii")
    except UnicodeError:
        return None

    if not hostname or len(hostname) > MAX_SOURCE_DOMAIN_LENGTH:
        return None
    if any(character.isspace() for character in hostname):
        return None
    return hostname


def normalize_source_url(
    value: Optional[str],
    *,
    fallback: Optional[str] = None,
) -> Optional[str]:
    """Strip query/fragment data and return a bounded HTTP(S) source URL.

    If ``fallback`` is supplied, a source URL with a different hostname is
    rejected in favor of the fallback origin. This prevents a caller from
    recording an arbitrary unrelated URL while the server still uses the
    request origin for embed authorization.
    """
    candidate = value.strip() if isinstance(value, str) else ""
    fallback_candidate = fallback.strip() if isinstance(fallback, str) else ""
    selected = candidate or fallback_candidate
    if not selected:
        return None
    if selected.lower() == "null":
        if fallback_candidate and fallback_candidate.lower() != "null":
            return normalize_source_url(fallback_candidate)
        return None

    if "://" not in selected:
        selected = f"https://{selected.lstrip('/')}"

    try:
        parsed = urlsplit(selected)
        if parsed.scheme.lower() not in {"http", "https"}:
            raise ValueError("source URL must use HTTP(S)")
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("source URL cannot contain credentials")
        port = parsed.port
        hostname = parsed.hostname
    except ValueError:
        if fallback_candidate and selected != fallback_candidate:
            return normalize_source_url(fallback_candidate)
        return None

    normalized_hostname = normalize_domain(hostname)
    fallback_hostname = normalize_domain(fallback_candidate)
    if not normalized_hostname:
        if fallback_candidate and selected != fallback_candidate:
            return normalize_source_url(fallback_candidate)
        return None

    if fallback_hostname and normalized_hostname != fallback_hostname:
        if selected != fallback_candidate:
            return normalize_source_url(fallback_candidate)
        return None

    if ":" in normalized_hostname and not normalized_hostname.startswith("["):
        netloc = f"[{normalized_hostname}]"
    else:
        netloc = normalized_hostname
    if port is not None:
        netloc = f"{netloc}:{port}"

    normalized = urlunsplit(
        (
            parsed.scheme.lower(),
            netloc,
            parsed.path or "/",
            "",
            "",
        )
    )
    if len(normalized) > MAX_SOURCE_URL_LENGTH:
        if fallback_candidate and selected != fallback_candidate:
            return normalize_source_url(fallback_candidate)
        return None
    return normalized
