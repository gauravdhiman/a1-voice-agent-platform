"""Shared OAuth identity models for backend redirect sign-in."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

OAuthProvider = Literal["google", "linkedin"]


@dataclass(frozen=True)
class OAuthVerifiedIdentity:
    """Verified identity returned after an OAuth authorization-code exchange."""

    provider: OAuthProvider
    email: str
    first_name: str
    last_name: str
    provider_sub: str
    picture: Optional[str] = None
    invitation_token: Optional[str] = None
