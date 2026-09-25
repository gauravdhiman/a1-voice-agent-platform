"""Persistence for organization-level critical notification destinations."""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from shared.common.security import decrypt_data, encrypt_data
from shared.config import supabase_config

from .organization_settings_models import (
    OrganizationNotificationSettings,
    OrganizationNotificationSettingsUpdate,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OrganizationNotificationDeliverySettings:
    """One consistent snapshot of private destinations used by the outbox."""

    sms_phone: Optional[str]
    telegram_chat_id: Optional[str]
    telegram_bot_token: Optional[str]
    telegram_bot_token_stored: bool


class OrganizationNotificationSettingsService:
    """Read and update destinations configured by an organization's admins."""

    TABLE = "organization_notification_settings"

    def __init__(self, *, supabase_config_override: Any = None) -> None:
        """Initialize with a replaceable database dependency."""
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

    def _get_row(self, organization_id: UUID) -> dict[str, Any]:
        """Load one organization settings row without returning secret material."""
        response = (
            self.supabase.table(self.TABLE)
            .select(
                "organization_id, alert_email, sms_phone, telegram_chat_id, "
                "telegram_bot_token_encrypted, updated_by, created_at, updated_at"
            )
            .eq("organization_id", str(organization_id))
            .limit(1)
            .execute()
        )
        data = getattr(response, "data", None)
        row = data[0] if isinstance(data, list) and data else data or {}
        return row if isinstance(row, dict) else {}

    @staticmethod
    def _decrypt_telegram_bot_token(encrypted_token: Optional[str]) -> Optional[str]:
        """Decrypt an organization bot token without logging secret values."""
        if not encrypted_token:
            return None
        payload = decrypt_data(encrypted_token)
        token = payload.get("token")
        return token if isinstance(token, str) and token else None

    async def get_settings(
        self, organization_id: UUID
    ) -> OrganizationNotificationSettings:
        """Return saved destinations and whether an organization bot token exists."""
        row = self._get_row(organization_id)
        encrypted_token = row.get("telegram_bot_token_encrypted")
        now = datetime.now(timezone.utc)
        return OrganizationNotificationSettings(
            organization_id=organization_id,
            alert_email=row.get("alert_email") or None,
            sms_phone=row.get("sms_phone") or None,
            telegram_chat_id=row.get("telegram_chat_id") or None,
            # The API reports whether a credential is stored without requiring
            # it to decrypt successfully. Delivery handles unreadable tokens
            # independently so they do not hide contact settings or block SMS.
            telegram_bot_configured=bool(encrypted_token),
            updated_by=row.get("updated_by"),
            created_at=row.get("created_at") or now,
            updated_at=row.get("updated_at") or now,
        )

    async def get_delivery_settings(
        self, organization_id: UUID
    ) -> OrganizationNotificationDeliverySettings:
        """Read channel destinations and the encrypted Telegram token together."""
        row = self._get_row(organization_id)
        encrypted_token = row.get("telegram_bot_token_encrypted")
        return OrganizationNotificationDeliverySettings(
            sms_phone=row.get("sms_phone") or None,
            telegram_chat_id=row.get("telegram_chat_id") or None,
            telegram_bot_token=self._decrypt_telegram_bot_token(encrypted_token),
            telegram_bot_token_stored=bool(encrypted_token),
        )

    async def update_settings(
        self,
        organization_id: UUID,
        payload: OrganizationNotificationSettingsUpdate,
        updated_by: UUID,
    ) -> OrganizationNotificationSettings:
        """Atomically save destinations and encrypt any supplied bot token."""
        patch = payload.model_dump(mode="json", exclude_unset=True)
        if "telegram_bot_token" in patch:
            token = patch.pop("telegram_bot_token")
            patch["telegram_bot_token_encrypted"] = (
                encrypt_data({"token": token}) if token else None
            )
        if not patch:
            return await self.get_settings(organization_id)

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
            if "ck_org_notification_sms_phone_e164" in error_text:
                raise ValueError("Enter a valid phone number in E.164 format.") from exc
            if "ck_org_notification_telegram_destination" in error_text:
                raise ValueError(
                    "Enter a valid Telegram chat ID or channel username."
                ) from exc
            logger.error(
                "Could not update organization notification settings (%s)",
                type(exc).__name__,
            )
            raise

        return await self.get_settings(organization_id)


organization_notification_settings_service = OrganizationNotificationSettingsService()
