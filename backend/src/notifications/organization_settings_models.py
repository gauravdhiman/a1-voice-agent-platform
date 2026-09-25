"""Models for organization-level critical notification destinations."""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class OrganizationNotificationSettings(BaseModel):
    """Organization notification destinations and Telegram credential status."""

    organization_id: UUID
    alert_email: Optional[EmailStr] = None
    sms_phone: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    telegram_bot_configured: bool = False
    updated_by: Optional[UUID] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class OrganizationNotificationSettingsUpdate(BaseModel):
    """Partial update for an organization's critical notification destinations."""

    model_config = ConfigDict(extra="forbid")

    alert_email: Optional[EmailStr] = None
    sms_phone: Optional[str] = Field(
        None,
        min_length=3,
        max_length=16,
        pattern=r"^\+[1-9]\d{1,14}$",
        description="SMS destination in E.164 format",
    )
    telegram_chat_id: Optional[str] = Field(
        None,
        max_length=100,
        pattern=r"^(-?\d{1,20}|@[A-Za-z0-9_]{5,32})$",
        description="Telegram numeric chat ID or public channel username",
    )
    telegram_bot_token: Optional[str] = Field(
        None,
        max_length=256,
        pattern=r"^\d{5,15}:[A-Za-z0-9_-]{20,}$",
        description="Bot token created for this organization with Telegram BotFather",
    )

    @field_validator(
        "alert_email",
        "sms_phone",
        "telegram_chat_id",
        "telegram_bot_token",
        mode="before",
    )
    @classmethod
    def normalize_destinations(cls, value: object) -> object:
        """Trim input and treat an empty value as an explicit clear."""
        if isinstance(value, str):
            return value.strip() or None
        return value
