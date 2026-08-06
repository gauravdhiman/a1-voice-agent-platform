"""Mint Supabase sessions after backend OAuth completes."""

from __future__ import annotations

import logging
from typing import Any, Optional
from uuid import UUID

from fastapi import HTTPException, status
from opentelemetry import trace
from src.organization.provisioning import ensure_default_organization_for_user
from src.shared.utils import extract_first_last_name
from supabase import Client

from shared.config import create_isolated_supabase_client, settings

try:
    from supabase_auth.errors import AuthApiError
except ImportError:  # pragma: no cover
    from gotrue.errors import AuthApiError

from .models import AuthResponse, UserProfile
from .oauth_identity import OAuthVerifiedIdentity

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


def _create_isolated_auth_client() -> Client:
    """Return a throwaway Supabase client for auth admin calls only."""
    return create_isolated_supabase_client()


class OAuthSessionService:
    """Create Supabase sessions for verified OAuth identities."""

    def __init__(self, auth_client_factory: Any = _create_isolated_auth_client) -> None:
        self._auth_client_factory = auth_client_factory

    @tracer.start_as_current_span("auth.oauth_session.complete_oauth_sign_in")
    async def complete_oauth_sign_in(
        self, identity: OAuthVerifiedIdentity
    ) -> tuple[Optional[AuthResponse], Optional[HTTPException]]:
        """Create or reuse a Supabase user and return a fresh session."""
        current_span = trace.get_current_span()
        current_span.set_attribute("user.email", identity.email)
        current_span.set_attribute("oauth.provider", identity.provider)

        auth_client = self._auth_client_factory()
        try:
            await self._ensure_supabase_user(auth_client, identity)
            session_response = self._verify_magic_link_session(
                auth_client, identity.email
            )
        except AuthApiError as error:
            logger.warning(
                "%s OAuth Supabase session creation failed: %s",
                identity.provider,
                error,
            )
            current_span.set_status(trace.Status(trace.StatusCode.ERROR, str(error)))
            return None, HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"{identity.provider.title()} authentication could not be completed.",
            )
        except Exception as error:  # pragma: no cover - defensive guard
            logger.error(
                "Unexpected %s OAuth Supabase session failure",
                identity.provider,
                exc_info=True,
            )
            current_span.set_status(trace.Status(trace.StatusCode.ERROR, str(error)))
            return None, HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"{identity.provider.title()} authentication could not be completed.",
            )

        user = session_response.user
        session = session_response.session
        if not user or not session:
            current_span.set_status(
                trace.Status(trace.StatusCode.ERROR, "missing_supabase_session")
            )
            return None, HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"{identity.provider.title()} authentication could not be completed.",
            )

        if identity.provider in {"google", "linkedin"}:
            self._sync_oauth_sign_in_metadata(auth_client, user, identity)

        org_name = (
            f"{identity.first_name}'s Organization" if identity.first_name else None
        )
        org_id, org_error = await ensure_default_organization_for_user(
            UUID(str(user.id)),
            identity.email,
            organization_name=org_name,
        )
        if org_error:
            logger.warning(
                "Default organization not provisioned for %s OAuth user %s: %s",
                identity.provider,
                user.id,
                org_error,
            )
        elif org_id:
            current_span.set_attribute("organization.id", str(org_id))

        user_metadata = user.user_metadata or {}
        first_name, last_name = extract_first_last_name(user_metadata)
        profile = UserProfile(
            id=user.id,
            email=user.email or identity.email,
            first_name=first_name or identity.first_name,
            last_name=last_name or identity.last_name,
            email_confirmed_at=_format_timestamp(user.email_confirmed_at) or None,
            created_at=_format_timestamp(user.created_at),
            updated_at=_format_timestamp(user.updated_at),
        )

        current_span.set_attribute("user.id", str(user.id))
        current_span.set_status(trace.Status(trace.StatusCode.OK))
        return (
            AuthResponse(
                user=profile,
                access_token=session.access_token,
                refresh_token=session.refresh_token,
                token_type="bearer",
                expires_in=session.expires_in or 3600,
            ),
            None,
        )

    async def _ensure_supabase_user(
        self, auth_client: Client, identity: OAuthVerifiedIdentity
    ) -> None:
        """Create the Supabase auth user when the OAuth email is new."""
        metadata = {
            "first_name": identity.first_name,
            "last_name": identity.last_name,
            f"{identity.provider}_sub": identity.provider_sub,
        }
        if identity.picture:
            metadata["avatar_url"] = identity.picture

        try:
            auth_client.auth.admin.create_user(
                {
                    "email": identity.email,
                    "email_confirm": True,
                    "user_metadata": metadata,
                }
            )
        except AuthApiError as error:
            message = str(error).lower()
            if "already" in message or "exists" in message:
                return
            raise

    def _sync_oauth_sign_in_metadata(
        self,
        auth_client: Client,
        user: Any,
        identity: OAuthVerifiedIdentity,
    ) -> None:
        """Persist OAuth provider metadata and last sign-in method for signup UX."""
        if identity.provider not in {"google", "linkedin"}:
            return

        metadata = dict(getattr(user, "user_metadata", None) or {})
        metadata.update(
            {
                "first_name": identity.first_name or metadata.get("first_name"),
                "last_name": identity.last_name or metadata.get("last_name"),
                f"{identity.provider}_sub": identity.provider_sub,
                "last_sign_in_method": identity.provider,
            }
        )
        if identity.picture:
            metadata["avatar_url"] = identity.picture

        try:
            auth_client.auth.admin.update_user_by_id(
                str(user.id),
                {"user_metadata": metadata},
            )
        except AuthApiError as error:
            logger.warning(
                "Failed to sync %s OAuth metadata for user %s: %s",
                identity.provider,
                user.id,
                error,
            )

    def _verify_magic_link_session(self, auth_client: Client, email: str) -> Any:
        """Generate and immediately verify a one-time login link server-side."""
        link_response = auth_client.auth.admin.generate_link(
            {"type": "magiclink", "email": email}
        )
        hashed_token = link_response.properties.hashed_token
        return auth_client.auth.verify_otp(
            {"token_hash": hashed_token, "type": "email"}
        )


def _format_timestamp(value: Any) -> str:
    """Format Supabase timestamp fields that may be datetime or ISO strings."""
    if value is None:
        return ""
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


oauth_session_service = OAuthSessionService()

# Backward-compatible alias used by existing imports/tests.
linkedin_supabase_session_service = oauth_session_service
