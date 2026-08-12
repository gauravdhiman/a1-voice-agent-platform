"""Persistence service for platform phone-number lifecycle settings."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID

from shared.config import settings, supabase_config

from .platform_settings_models import (
    PHONE_NUMBER_SETTINGS_SINGLETON_ID,
    PlatformPhoneNumberSettings,
    PlatformPhoneNumberSettingsUpdate,
)

logger = logging.getLogger(__name__)


class PlatformPhoneNumberSettingsService:
    """Read and update the singleton phone-number lifecycle configuration.

    The database row is the source of truth for platform-admin changes. The
    environment-backed application settings remain the fallback when the
    settings table is unavailable during deployment or a transient database
    failure occurs.
    """

    TABLE = "platform_phone_number_settings"

    @property
    def supabase(self):
        if not supabase_config.is_configured():
            raise ValueError("Supabase is not configured")
        return supabase_config.client

    def _environment_defaults(self) -> PlatformPhoneNumberSettings:
        """Build settings from environment defaults for safe fallback paths."""
        now = datetime.now(timezone.utc)
        return PlatformPhoneNumberSettings(
            id=PHONE_NUMBER_SETTINGS_SINGLETON_ID,
            billing_grace_period_days=int(
                settings.phone_number_billing_grace_period_days
            ),
            billing_check_interval_hours=float(
                settings.phone_number_billing_check_interval_hours
            ),
            release_retry_interval_hours=float(
                settings.phone_number_release_retry_interval_hours
            ),
            created_at=now,
            updated_at=now,
        )

    @staticmethod
    def _from_row(row: dict) -> PlatformPhoneNumberSettings:
        """Convert a database row into the public response model."""
        return PlatformPhoneNumberSettings(
            id=UUID(row["id"]),
            billing_grace_period_days=int(row["billing_grace_period_days"]),
            billing_check_interval_hours=float(row["billing_check_interval_hours"]),
            release_retry_interval_hours=float(row["release_retry_interval_hours"]),
            updated_by=UUID(row["updated_by"]) if row.get("updated_by") else None,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    async def get_settings(
        self, *, allow_fallback: bool = True
    ) -> PlatformPhoneNumberSettings:
        """Return current settings, optionally falling back to environment values."""
        try:
            response = (
                self.supabase.table(self.TABLE)
                .select("*")
                .eq("id", str(PHONE_NUMBER_SETTINGS_SINGLETON_ID))
                .single()
                .execute()
            )
            return self._from_row(response.data)
        except Exception:
            if not allow_fallback:
                raise
            logger.warning(
                "Falling back to environment phone-number settings", exc_info=True
            )
            return self._environment_defaults()

    async def update_settings(
        self,
        payload: PlatformPhoneNumberSettingsUpdate,
        updated_by: UUID,
    ) -> PlatformPhoneNumberSettings:
        """Update platform-admin settings and return the persisted values."""
        update_data: dict = {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "updated_by": str(updated_by),
        }
        if payload.billing_grace_period_days is not None:
            update_data["billing_grace_period_days"] = payload.billing_grace_period_days
        if payload.billing_check_interval_hours is not None:
            update_data["billing_check_interval_hours"] = (
                payload.billing_check_interval_hours
            )
        if payload.release_retry_interval_hours is not None:
            update_data["release_retry_interval_hours"] = (
                payload.release_retry_interval_hours
            )

        self.supabase.table(self.TABLE).update(update_data).eq(
            "id", str(PHONE_NUMBER_SETTINGS_SINGLETON_ID)
        ).execute()
        return await self.get_settings(allow_fallback=False)


platform_phone_number_settings_service = PlatformPhoneNumberSettingsService()
