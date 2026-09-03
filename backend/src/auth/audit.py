"""Append-only authentication audit trail (Epic E hardening).

Security-relevant auth events are recorded to ``auth_audit_events`` by the
backend only. Logging never raises and never blocks the request it
observes. No tokens, passwords, or request bodies are recorded.
"""

from __future__ import annotations

import logging
from typing import Any, Optional
from uuid import UUID

logger = logging.getLogger(__name__)

#: Events the ``auth_audit_events`` check constraint accepts.
SIGNUP = "signup"
SIGNUP_DENIED = "signup_denied"
SIGNIN = "signin"
SIGNIN_DENIED = "signin_denied"
SIGNOUT = "signout"
INVITATION_PROCESSED = "invitation_processed"
PASSWORD_RESET_REQUESTED = "password_reset_requested"
OAUTH_SIGNIN = "oauth_signin"
OAUTH_DENIED = "oauth_denied"


def _client_ip(request: Any) -> Optional[str]:
    """Extract the caller IP without failing on test doubles."""
    try:
        client = getattr(request, "client", None)
        host = getattr(client, "host", None)
        return str(host)[:64] if host else None
    except Exception:
        return None


def _user_agent(request: Any) -> Optional[str]:
    """Extract a bounded user-agent string without failing."""
    try:
        headers = getattr(request, "headers", None)
        agent = headers.get("user-agent") if headers is not None else None
        return str(agent)[:500] if agent else None
    except Exception:
        return None


async def log_auth_event(
    event: str,
    *,
    email: Optional[str] = None,
    user_id: Optional[UUID] = None,
    request: Any = None,
    metadata: Optional[dict[str, Any]] = None,
    supabase: Any = None,
) -> None:
    """Append one audit event; never raises.

    Args:
        event: One of the module event constants.
        email: Account email when known (stored for investigation).
        user_id: Account id when known.
        request: FastAPI request used for IP/user-agent only.
        metadata: Small JSON-safe extras (provider, reason codes).
        supabase: Service-role client. When None the event is dropped
            with a warning (tests and unconfigured environments).
    """
    if supabase is None:
        logger.warning("Auth audit dropped (no client) event=%s", event)
        return
    row = {
        "user_id": str(user_id) if user_id is not None else None,
        "email": email.strip().lower()[:320] if email else None,
        "event": event,
        "ip": _client_ip(request),
        "user_agent": _user_agent(request),
        "metadata": metadata or {},
    }
    try:
        supabase.table("auth_audit_events").insert(row).execute()
    except Exception:
        logger.error("Auth audit insert failed event=%s", event, exc_info=True)
