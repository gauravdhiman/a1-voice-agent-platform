"""Persistence for organization-level critical notification destinations."""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from shared.config import supabase_config

from .organization_settings_models import (
    OrganizationNotificationSettings,
    OrganizationNotificationSettingsUpdate,
)
from .platform_settings_service import platform_notification_settings_service

logger = logging.getLogger(__name__)


class OrganizationNotificationSettingsService:
    """Read and update destinations configured by an organization's admins."""

    TABLE = "organization_notification_settings"

    def __init__(
        self,
        *,
        platform_settings_service: Any = None,
        supabase_config_override: Any = None,
    ) -> None:
        """Initialize with replaceable provider-settings and database dependencies."""
        self.platform_settings_service = (
            platform_settings_service
            if platform_settings_service is not None
            else platform_notification_settings_service
        )
        self._supabase_config = (
            supabase_config_override
            if supabase_config_override is not None
            else supabase_config
        )

    @property
    def supabase(self):
        """Return the service-role client used for tenant settings persistence."""
        client = self._supabase_config.service_client or self._supabase_config.client
        if client is None:
            raise ValueError("Supabase is not configured")
        return client

    async def get_settings(
        self, organization_id: UUID
    ) -> OrganizationNotificationSettings:
        """Return destinations and current provider readiness for one organization."""
        response = (
            self.supabase.table(self.TABLE)
            .select("*")
            .eq("organization_id", str(organization_id))
            .limit(1)
            .execute()
        )
        data = getattr(response, "data", None)
        row = data[0] if isinstance(data, list) and data else data or {}
        if not isinstance(row, dict):
            row = {}

        try:
            platform_settings = await self.platform_settings_service.get_settings()
            sms_sender_configured = bool(
                getattr(platform_settings, "sms_sender_configured", False)
            )
            telegram_bot_configured = bool(
                getattr(platform_settings, "telegram_bot_token_configured", False)
            )
        except Exception as exc:
            logger.warning(
                "Could not resolve notification provider readiness (%s)",
                type(exc).__name__,
            )
            sms_sender_configured = False
            telegram_bot_configured = False

        now = datetime.now(timezone.utc)
        return OrganizationNotificationSettings(
            organization_id=organization_id,
            alert_email=row.get("alert_email") or None,
            sms_phone=row.get("sms_phone") or None,
            sms_enabled=bool(row.get("sms_enabled", False)),
            telegram_chat_id=row.get("telegram_chat_id") or None,
            telegram_enabled=bool(row.get("telegram_enabled", False)),
            sms_sender_configured=sms_sender_configured,
            telegram_bot_configured=telegram_bot_configured,
            updated_by=row.get("updated_by"),
            created_at=row.get("created_at") or now,
            updated_at=row.get("updated_at") or now,
        )

    async def update_settings(
        self,
        organization_id: UUID,
        payload: OrganizationNotificationSettingsUpdate,
        updated_by: UUID,
    ) -> OrganizationNotificationSettings:
        """Atomically apply supplied fields and enforce enabled-channel destinations."""
        patch = payload.model_dump(mode="json", exclude_unset=True)
        current = await self.get_settings(organization_id)
        values = {
            "sms_phone": current.sms_phone,
            "sms_enabled": current.sms_enabled,
            "telegram_chat_id": current.telegram_chat_id,
            "telegram_enabled": current.telegram_enabled,
        }
        values.update(patch)

        if values["sms_enabled"] and not values["sms_phone"]:
            raise ValueError("Enter a phone number before enabling SMS alerts.")
        if values["telegram_enabled"] and not values["telegram_chat_id"]:
            raise ValueError(
                "Enter a Telegram chat ID before enabling Telegram alerts."
            )
        if not patch:
            return current

        try:
            response = self.supabase.rpc(
                "update_organization_notification_settings",
                {
                    "p_organization_id": str(organization_id),
                    "p_updated_by": str(updated_by),
                    "p_updates": patch,
                },
            ).execute()
            error = getattr(response, "error", None)
            if error:
                raise RuntimeError(str(error))
        except Exception as exc:
            error_text = str(exc).lower()
            if "ck_org_notification_sms_enabled_has_phone" in error_text:
                raise ValueError(
                    "Enter a phone number before enabling SMS alerts."
                ) from exc
            if "ck_org_notification_telegram_enabled_has_chat_id" in error_text:
                raise ValueError(
                    "Enter a Telegram chat ID before enabling Telegram alerts."
                ) from exc
            logger.error(
                "Could not update organization notification settings (%s)",
                type(exc).__name__,
            )
            raise

        return await self.get_settings(organization_id)


organization_notification_settings_service = OrganizationNotificationSettingsService()
