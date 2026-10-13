"""Backward-compatible re-exports for LinkedIn OAuth session minting."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import HTTPException

from .linkedin_oauth import LinkedInVerifiedIdentity
from .models import AuthResponse
from .oauth_identity import OAuthVerifiedIdentity
from .oauth_session import (
    OAuthSessionService,
    _create_isolated_auth_client,
    oauth_session_service,
)


class LinkedInSupabaseSessionService(OAuthSessionService):
    """Deprecated alias kept for existing imports and tests."""

    def __init__(
        self,
        supabase_client: Any | None = None,
        auth_client_factory: Any | None = None,
    ) -> None:
        if auth_client_factory is None and supabase_client is not None:
            auth_client_factory = lambda: supabase_client
        super().__init__(
            auth_client_factory=auth_client_factory or _create_isolated_auth_client
        )

    async def create_session(
        self, identity: LinkedInVerifiedIdentity | OAuthVerifiedIdentity
    ) -> tuple[Optional[AuthResponse], Optional[HTTPException]]:
        if isinstance(identity, LinkedInVerifiedIdentity):
            identity = OAuthVerifiedIdentity(
                provider="linkedin",
                email=identity.email,
                first_name=identity.first_name,
                last_name=identity.last_name,
                provider_sub=identity.linkedin_sub,
                picture=identity.picture,
                terms_accepted=identity.terms_accepted,
            )
        return await self.complete_oauth_sign_in(identity)


linkedin_supabase_session_service = LinkedInSupabaseSessionService()

__all__ = [
    "LinkedInSupabaseSessionService",
    "linkedin_supabase_session_service",
    "oauth_session_service",
]
