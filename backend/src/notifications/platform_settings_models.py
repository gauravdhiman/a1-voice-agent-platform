"""
Pydantic models for platform notification settings.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from src.auth.models import AuthEmail

PLATFORM_SETTINGS_SINGLETON_ID = UUID("00000000-0000-0000-0000-000000000001")


def extract_telegram_bot_id(token: str) -> Optional[str]:
    """Return the public numeric bot id prefix from a Telegram bot token."""
    if not token or ":" not in token:
        return None
    prefix = token.split(":", 1)[0].strip()
    return prefix if prefix.isdigit() else None


def verification_sender_configured(
    from_email: Optional[str], from_name: Optional[str]
) -> bool:
    """Return True when both verification sender fields are non-empty."""
    return bool(
        from_email
        and str(from_email).strip()
        and from_name
        and str(from_name).strip()
    )


class PlatformNotificationSettings(BaseModel):
    """Platform-wide notification configuration (singleton row)."""

    id: UUID
    verification_from_email: Optional[EmailStr] = None
    verification_from_name: Optional[str] = Field(None, max_length=100)
    email_verification_active: bool = Field(
        False,
        description="True when From email and From name are both configured",
    )
    telegram_chat_id: Optional[str] = Field(None, max_length=100)
    telegram_notifications_enabled: bool = False
    telegram_bot_token_configured: bool = False
    telegram_bot_id: Optional[str] = Field(
        None,
        description="Public numeric bot id (prefix before ':' in the token)",
    )
    updated_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime


class PlatformNotificationSettingsUpdate(BaseModel):
    """Update payload for platform notification settings."""

    verification_from_email: Optional[EmailStr] = None
    verification_from_name: Optional[str] = Field(None, max_length=100)
    telegram_chat_id: Optional[str] = Field(None, max_length=100)
    telegram_notifications_enabled: Optional[bool] = None
    telegram_bot_token: Optional[str] = Field(
        None,
        max_length=256,
        description="Plaintext bot token; stored encrypted server-side",
    )


class ResendVerificationRequest(BaseModel):
    """Request to resend an email verification link."""

    email: AuthEmail


class VerifyEmailRequest(BaseModel):
    """Request to verify an email address with a token."""

    token: str = Field(..., min_length=16, max_length=255)


class VerifyEmailResponse(BaseModel):
    """Response after verifying an email address."""

    success: bool
    message: str
