"""
Service for managing platform notification settings (singleton).
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Tuple
from uuid import UUID

from shared.common.security import decrypt_data, encrypt_data
from shared.config import supabase_config

from .platform_settings_models import (
    PLATFORM_SETTINGS_SINGLETON_ID,
    PlatformNotificationSettings,
    PlatformNotificationSettingsUpdate,
    extract_telegram_bot_id,
    verification_sender_configured,
)

logger = logging.getLogger(__name__)


class PlatformNotificationSettingsService:
    """Read and update the platform notification settings singleton."""

    TABLE = "platform_notification_settings"

    @property
    def supabase(self):
        if not supabase_config.is_configured():
            raise ValueError("Supabase is not configured")
        return supabase_config.client

    async def get_settings(self) -> PlatformNotificationSettings:
        """Return current platform notification settings."""
        response = (
            self.supabase.table(self.TABLE)
            .select("*")
            .eq("id", str(PLATFORM_SETTINGS_SINGLETON_ID))
            .single()
            .execute()
        )
        row = response.data
        token_encrypted = row.get("telegram_bot_token_encrypted")
        telegram_bot_id = self._read_telegram_bot_id(token_encrypted)
        platform_admin_email = row.get("platform_admin_email")
        from_email = row.get("verification_from_email")
        from_name = row.get("verification_from_name")
        return PlatformNotificationSettings(
            id=UUID(row["id"]),
            platform_admin_email=platform_admin_email,
            verification_from_email=from_email,
            verification_from_name=from_name,
            email_verification_active=verification_sender_configured(
                from_email, from_name
            ),
            telegram_chat_id=row.get("telegram_chat_id"),
            telegram_notifications_enabled=bool(
                row.get("telegram_notifications_enabled")
            ),
            telegram_bot_token_configured=bool(token_encrypted),
            telegram_bot_id=telegram_bot_id,
            updated_by=UUID(row["updated_by"]) if row.get("updated_by") else None,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    async def update_settings(
        self,
        payload: PlatformNotificationSettingsUpdate,
        updated_by: UUID,
    ) -> PlatformNotificationSettings:
        """Update platform notification settings."""
        update_data: dict = {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "updated_by": str(updated_by),
        }

        # Optional fields use explicit null as a clear operation.  Check which
        # fields the caller supplied so omitted values remain unchanged while
        # the admin UI can clear previously saved values.
        fields_set = payload.model_fields_set

        if "platform_admin_email" in fields_set:
            update_data["platform_admin_email"] = payload.platform_admin_email
        if "verification_from_email" in fields_set:
            update_data["verification_from_email"] = payload.verification_from_email
        if "verification_from_name" in fields_set:
            update_data["verification_from_name"] = payload.verification_from_name
        if "telegram_chat_id" in fields_set:
            update_data["telegram_chat_id"] = payload.telegram_chat_id
        if "telegram_notifications_enabled" in fields_set:
            update_data["telegram_notifications_enabled"] = (
                payload.telegram_notifications_enabled
            )
        if "telegram_bot_token" in fields_set:
            token = (payload.telegram_bot_token or "").strip()
            if token:
                update_data["telegram_bot_token_encrypted"] = encrypt_data(
                    {
                        "token": token,
                        "bot_id": extract_telegram_bot_id(token),
                    }
                )
            else:
                update_data["telegram_bot_token_encrypted"] = None

        self.supabase.table(self.TABLE).update(update_data).eq(
            "id", str(PLATFORM_SETTINGS_SINGLETON_ID)
        ).execute()

        return await self.get_settings()

    async def is_email_verification_required(self) -> bool:
        """Return whether signup/sign-in should enforce email verification."""
        settings = await self.get_settings()
        return settings.email_verification_active

    @staticmethod
    def _read_telegram_bot_id(token_encrypted: Optional[str]) -> Optional[str]:
        """Extract public bot id from stored encrypted token payload."""
        if not token_encrypted:
            return None
        try:
            decrypted = decrypt_data(token_encrypted)
        except Exception:
            logger.warning("Could not decrypt telegram bot token for bot id display")
            return None
        bot_id = decrypted.get("bot_id")
        if bot_id:
            return str(bot_id)
        token = decrypted.get("token")
        if isinstance(token, str):
            return extract_telegram_bot_id(token)
        return None

    async def get_verification_sender(
        self,
    ) -> Tuple[Optional[str], Optional[str]]:
        """Return (from_email, from_name) for verification emails."""
        settings_row = await self.get_settings()
        return settings_row.verification_from_email, settings_row.verification_from_name

    async def get_platform_admin_email(self) -> Optional[str]:
        """Return the configured recipient for platform-admin lead alerts."""
        settings_row = await self.get_settings()
        return settings_row.platform_admin_email

    async def get_telegram_credentials(
        self,
    ) -> Tuple[Optional[str], Optional[str], bool]:
        """Return (bot_token, chat_id, enabled) for Telegram alerts."""
        response = (
            self.supabase.table(self.TABLE)
            .select(
                "telegram_bot_token_encrypted, telegram_chat_id, "
                "telegram_notifications_enabled"
            )
            .eq("id", str(PLATFORM_SETTINGS_SINGLETON_ID))
            .single()
            .execute()
        )
        row = response.data
        enabled = bool(row.get("telegram_notifications_enabled"))
        chat_id = row.get("telegram_chat_id")
        token_encrypted = row.get("telegram_bot_token_encrypted")
        if not token_encrypted:
            return None, chat_id, enabled

        decrypted = decrypt_data(token_encrypted)
        return decrypted.get("token"), chat_id, enabled


platform_notification_settings_service = PlatformNotificationSettingsService()
