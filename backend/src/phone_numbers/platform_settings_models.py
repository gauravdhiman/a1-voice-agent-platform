"""Models for platform-admin phone-number lifecycle settings."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

PHONE_NUMBER_SETTINGS_SINGLETON_ID = UUID("00000000-0000-0000-0000-000000000002")


class PlatformPhoneNumberSettings(BaseModel):
    """Platform-wide phone-number billing and retry settings."""

    id: UUID
    billing_grace_period_days: int = Field(ge=1)
    billing_check_interval_hours: float = Field(gt=0)
    release_retry_interval_hours: float = Field(gt=0)
    updated_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime


class PlatformPhoneNumberSettingsUpdate(BaseModel):
    """Partial update payload for phone-number lifecycle settings."""

    billing_grace_period_days: Optional[int] = Field(default=None, ge=1)
    billing_check_interval_hours: Optional[float] = Field(default=None, gt=0)
    release_retry_interval_hours: Optional[float] = Field(default=None, gt=0)
