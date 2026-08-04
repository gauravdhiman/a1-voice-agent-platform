"""IANA timezone validation and resolution for organization-scoped voice sessions."""

from __future__ import annotations

import logging
from typing import Any, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

logger = logging.getLogger(__name__)


def validate_iana_timezone(name: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    """Validate an IANA timezone name.

    Args:
        name: Candidate timezone (e.g. ``America/Phoenix``). ``None`` or blank
            means unset — not an error.

    Returns:
        A tuple of ``(normalized_name, error_message)``. On success ``error_message``
        is ``None``. On invalid input ``normalized_name`` is ``None``.
    """
    if name is None:
        return None, None
    stripped = name.strip()
    if not stripped:
        return None, None
    try:
        ZoneInfo(stripped)
    except ZoneInfoNotFoundError:
        return None, f"Invalid IANA timezone: {stripped!r}"
    return stripped, None


def normalize_timezone_input(
    value: Optional[str],
) -> tuple[Optional[str], Optional[str]]:
    """Normalize user/API timezone input before persistence.

    Args:
        value: Raw timezone string from a form or API payload.

    Returns:
        Same shape as :func:`validate_iana_timezone` — ``(stored_value, error)``.
        Blank input clears the column (``None``).
    """
    if value is None:
        return None, None
    return validate_iana_timezone(value.strip())


def resolve_organization_timezone(
    org: Optional[Any],
    *,
    platform_default: Optional[str] = None,
) -> str:
    """Pick the timezone used to anchor agent prompts for a call.

    Resolution order:

    1. ``org.timezone`` when set and valid
    2. ``platform_default`` (typically ``AGENT_DEFAULT_TIMEZONE`` env) when valid
    3. ``UTC``

    Args:
        org: Organization-like object with optional ``timezone`` attribute.
        platform_default: Dev/platform fallback when the org has no timezone.

    Returns:
        A valid IANA timezone name, never empty.
    """
    org_tz = getattr(org, "timezone", None) if org is not None else None
    if org_tz:
        normalized, error = validate_iana_timezone(org_tz)
        if normalized:
            return normalized
        if error:
            logger.warning(
                "Organization timezone %r is invalid (%s); falling back",
                org_tz,
                error,
            )

    if platform_default:
        normalized, _ = validate_iana_timezone(platform_default)
        if normalized:
            return normalized

    return "UTC"
