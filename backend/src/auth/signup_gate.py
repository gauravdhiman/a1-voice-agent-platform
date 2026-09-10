"""Closed-signup gate for the controlled-SaaS launch.

When ``PUBLIC_SIGNUP_ENABLED`` is false, new accounts may only be created
through an invitation token or by an allowlisted platform admin. Everyone
else is directed to the interest form (``/request-demo``).

Enforcement points (all in ``src.auth.routes``):

- ``POST /api/v1/auth/signup`` — hard 403 ``signup_disabled``.
- Google/LinkedIn OAuth callbacks — error redirect *after* the provider
  exchange, because the caller's email is only known then. The
  ``/authorize`` endpoints intentionally stay open: starting an OAuth flow
  creates no account and costs nothing.
- The frontend ``/auth/signup`` page redirects to ``/request-demo`` based
  on ``GET /api/v1/auth/signup-status`` (defense in depth; the backend
  gate is authoritative).

Known gap (Epic E): frontend-direct Supabase Auth calls
(``signInWithOAuth`` / GIS id-token) bypass this module. The hardening
follow-up disables direct providers in the Supabase dashboard so all
browser OAuth flows through the backend broker.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from shared.config import settings

logger = logging.getLogger(__name__)

#: Machine-readable marker in the 403 detail so the frontend can redirect
#: to the interest form without parsing human copy.
SIGNUP_DISABLED_CODE = "signup_disabled"

SIGNUP_DISABLED_MESSAGE = (
    "Public signup is currently invite-only while we onboard businesses "
    "with a concierge setup. Please request a demo and we will invite you."
)

#: Invitation rows in these states can never admit a signup. ``revoked`` is
#: retained for compatibility with historical rows from an older schema.
_CLOSED_INVITATION_STATUSES = frozenset({"accepted", "expired", "cancelled", "revoked"})


def is_allowlisted(email: str) -> bool:
    """Return True when the email bypasses the closed gate.

    Args:
        email: Caller-supplied email address (case-insensitive).

    Returns:
        True for ``PLATFORM_ADMIN_ALLOWLIST`` members.
    """
    return email.strip().lower() in set(settings.platform_admin_allowlist)


async def invitation_token_usable(
    token: str, supabase: Any, email: Optional[str] = None
) -> bool:
    """Check an invitation token without side effects.

    Unlike ``organization_service.process_invitation`` (which assigns roles
    and marks the row accepted), this is a read-only gate check: the token
    exists, is not in a closed state, and has not expired.

    Args:
        token: Invitation token from the signup request.
        supabase: Service-role Supabase client used for the lookup.
        email: Authenticated/signup email that must match the invitation when
            supplied. Closed signup always supplies this value.

    Returns:
        True when the token can admit exactly one signup.
    """
    try:
        response = (
            supabase.table("invitations")
            .select("id,email,status,expires_at")
            .eq("token", token)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.error("Signup gate invitation lookup failed", exc_info=True)
        return False

    rows = getattr(response, "data", None) or []
    if not rows:
        return False
    row = rows[0]
    if (
        email is not None
        and str(row.get("email", "")).strip().lower() != email.strip().lower()
    ):
        return False
    if str(row.get("status", "")).lower() in _CLOSED_INVITATION_STATUSES:
        return False
    if str(row.get("status", "")).lower() != "pending":
        return False
    expires_at = row.get("expires_at")
    if expires_at:
        try:
            deadline = datetime.fromisoformat(str(expires_at).replace("Z", "+00:00"))
        except ValueError:
            return False
        if datetime.now(timezone.utc) > deadline:
            return False
    return True


async def is_signup_allowed(
    email: str,
    invitation_token: Optional[str] = None,
    supabase: Any = None,
) -> tuple[bool, Optional[str]]:
    """Decide whether a signup attempt passes the controlled-SaaS gate.

    Args:
        email: Caller-supplied email address.
        invitation_token: Optional invitation token from the request.
        supabase: Service-role client for the invitation lookup. Required
            only when the gate is closed and an invitation token is present.

    Returns:
        Tuple of (allowed, denial_reason). ``denial_reason`` is None when
        allowed, otherwise ``SIGNUP_DISABLED_CODE`` (unknown/expired
        invitation tokens are denied with the same code so token validity
        cannot be probed through the gate).
    """
    if settings.public_signup_enabled:
        return True, None
    if is_allowlisted(email):
        return True, None
    if invitation_token and supabase is not None:
        if await invitation_token_usable(invitation_token, supabase, email):
            return True, None
    return False, SIGNUP_DISABLED_CODE
