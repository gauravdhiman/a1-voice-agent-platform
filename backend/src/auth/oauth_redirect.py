"""Frontend redirect helpers for backend-completed OAuth flows."""

from __future__ import annotations

from urllib.parse import urlencode

from shared.config import settings

from .models import AuthResponse
from .oauth_handoff import create_session_handoff_token


def oauth_error_redirect(message: str) -> str:
    """Build a frontend error redirect URL for failed OAuth flows."""
    base = settings.app_base_url.rstrip("/")
    return f"{base}/auth/session?{urlencode({'error': message})}"


def oauth_session_redirect(
    auth_response: AuthResponse,
    *,
    invitation_token: str | None = None,
) -> str:
    """Build a frontend redirect URL with a one-time session handoff code.

    Browsers do not preserve URL fragments on HTTP 302 redirects, so session
    tokens cannot be delivered in the hash. Instead the backend issues a short-
    lived signed ``handoff`` query parameter that the frontend exchanges once
    for Supabase session tokens.
    """
    base = settings.app_base_url.rstrip("/")
    query_params: dict[str, str] = {
        "handoff": create_session_handoff_token(auth_response),
    }
    if invitation_token:
        query_params["invitation_token"] = invitation_token

    return f"{base}/auth/session?{urlencode(query_params)}"
