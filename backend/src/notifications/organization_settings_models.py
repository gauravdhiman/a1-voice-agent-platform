"""Models for organization-level critical notification destinations."""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class OrganizationNotificationSettings(BaseModel):
    """Organization notification destinations and provider readiness."""

    organization_id: UUID
    alert_email: Optional[EmailStr] = None
    sms_phone: Optional[str] = None
    sms_enabled: bool = False
    telegram_chat_id: Optional[str] = None
    telegram_enabled: bool = False
    sms_sender_configured: bool = False
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
    sms_enabled: Optional[bool] = None
    telegram_chat_id: Optional[str] = Field(
        None,
        max_length=100,
        pattern=r"^(-?\d{1,20}|@[A-Za-z0-9_]{5,32})$",
        description="Telegram numeric chat ID or public channel username",
    )
    telegram_enabled: Optional[bool] = None

    @field_validator("alert_email", "sms_phone", "telegram_chat_id", mode="before")
    @classmethod
    def normalize_destinations(cls, value: object) -> object:
        """Trim destination input and treat an empty field as an explicit clear."""
        if isinstance(value, str):
            return value.strip() or None
        return value

    @field_validator("sms_enabled", "telegram_enabled")
    @classmethod
    def require_boolean_when_present(cls, value: Optional[bool]) -> Optional[bool]:
        """Reject explicit null toggles while keeping omitted fields optional."""
        if value is None:
            raise ValueError("Notification channel settings must be true or false.")
        return value
