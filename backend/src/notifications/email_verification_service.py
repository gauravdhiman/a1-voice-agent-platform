"""
Email verification token lifecycle and Resend delivery.
"""

import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from uuid import UUID

from shared.config import settings, supabase_config

from .models import SendNotificationRequest
from .platform_settings_service import platform_notification_settings_service
from .service import notification_service

logger = logging.getLogger(__name__)

VERIFICATION_TOKEN_BYTES = 32
DEFAULT_EXPIRY_HOURS = 24


class EmailVerificationService:
    """Create, send, and consume email verification tokens."""

    TABLE = "email_verification_tokens"

    @property
    def supabase(self):
        if not supabase_config.is_configured():
            raise ValueError("Supabase is not configured")
        client = supabase_config.service_client
        if client is None:
            raise ValueError("Supabase service client is not available")
        return client

    def _generate_token(self) -> str:
        return secrets.token_urlsafe(VERIFICATION_TOKEN_BYTES)

    def _parse_expires_at(self, value: str) -> datetime:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))

    def _get_active_token_row(self, user_id: UUID) -> Optional[dict]:
        """Return an unused, unexpired verification row for the user if one exists."""
        response = (
            self.supabase.table(self.TABLE)
            .select("token, expires_at, used_at")
            .eq("user_id", str(user_id))
            .limit(1)
            .execute()
        )
        rows = response.data or []
        if not rows:
            return None

        row = rows[0]
        if row.get("used_at"):
            return None

        if self._parse_expires_at(row["expires_at"]) < datetime.now(timezone.utc):
            return None

        return row

    def _find_token_row(self, token: str) -> Optional[dict]:
        """Look up a verification token row, tolerating empty Supabase responses."""
        response = (
            self.supabase.table(self.TABLE)
            .select("*")
            .eq("token", token)
            .limit(1)
            .execute()
        )
        rows = response.data or []
        return rows[0] if rows else None

    async def create_and_send_verification(
        self,
        user_id: UUID,
        email: str,
        user_name: str,
        *,
        expiry_hours: int = DEFAULT_EXPIRY_HOURS,
    ) -> Tuple[bool, Optional[str]]:
        """Create a verification token and send the email via Resend."""
        active_row = self._get_active_token_row(user_id)
        if active_row:
            token = active_row["token"]
            expires_at = self._parse_expires_at(active_row["expires_at"])
        else:
            token = self._generate_token()
            expires_at = datetime.now(timezone.utc) + timedelta(hours=expiry_hours)

            upsert_response = (
                self.supabase.table(self.TABLE)
                .upsert(
                    {
                        "user_id": str(user_id),
                        "token": token,
                        "expires_at": expires_at.isoformat(),
                        "used_at": None,
                    },
                    on_conflict="user_id",
                )
                .execute()
            )
            if not upsert_response or not upsert_response.data:
                logger.error(
                    "Failed to persist verification token for user %s", user_id
                )
                return False, "Failed to create verification token."

        remaining_hours = max(
            1,
            int(
                (expires_at - datetime.now(timezone.utc)).total_seconds() // 3600
            )
            or 1,
        )

        verification_url = (
            f"{settings.app_base_url.rstrip('/')}/auth/verify-email?token={token}"
        )

        from_email, from_name = (
            await platform_notification_settings_service.get_verification_sender()
        )

        request = SendNotificationRequest(
            event_key="user.email_verification",
            recipient_email=email,
            recipient_name=user_name,
            user_id=user_id,
            template_variables={
                "user_name": user_name,
                "verification_url": verification_url,
                "expiry_hours": str(remaining_hours),
            },
            template_id=None,
        )

        if from_email or from_name:
            sent, message = await self._send_with_sender_override(
                request, from_email=from_email, from_name=from_name
            )
            if not sent:
                return False, message
        else:
            response = await notification_service.send_notification(request)
            if not response.success:
                return False, response.message

        return True, None

    async def _send_with_sender_override(
        self,
        request: SendNotificationRequest,
        *,
        from_email: Optional[str],
        from_name: Optional[str],
    ) -> Tuple[bool, Optional[str]]:
        """Send notification using platform-configured sender when set."""
        original_from_email = notification_service.from_email
        original_from_name = notification_service.from_name
        try:
            if from_email:
                notification_service.from_email = from_email
            if from_name:
                notification_service.from_name = from_name
            response = await notification_service.send_notification(request)
            if not response.success:
                return False, response.message
            return True, None
        finally:
            notification_service.from_email = original_from_email
            notification_service.from_name = original_from_name

    async def verify_token(self, token: str) -> Tuple[bool, str]:
        """Validate token, confirm user email in Supabase, mark token used."""
        row = self._find_token_row(token)
        if not row:
            return (
                False,
                "This verification link is invalid or outdated. "
                "Please use the most recent verification email or request a new one.",
            )

        if row.get("used_at"):
            return False, "This verification link has already been used."

        expires_at = self._parse_expires_at(row["expires_at"])
        if expires_at < datetime.now(timezone.utc):
            return False, "This verification link has expired."

        user_id = row["user_id"]
        self.supabase.auth.admin.update_user_by_id(
            user_id,
            {"email_confirm": True},
        )

        self.supabase.table(self.TABLE).update(
            {"used_at": datetime.now(timezone.utc).isoformat()}
        ).eq("token", token).execute()

        return True, "Email verified successfully. You can now sign in."

    async def resend_verification(self, email: str) -> Tuple[bool, str]:
        """Resend verification email for an unverified user."""
        from src.auth.service import auth_service

        user = await auth_service._find_auth_user_by_email(email)
        if not user:
            return True, "If an account exists, a verification email has been sent."

        if getattr(user, "email_confirmed_at", None):
            return False, "This email address is already verified."

        metadata = getattr(user, "user_metadata", None) or {}
        first_name = metadata.get("first_name") or "User"
        last_name = metadata.get("last_name") or ""
        user_name = f"{first_name} {last_name}".strip() or first_name

        success, error = await self.create_and_send_verification(
            UUID(str(user.id)),
            email,
            user_name,
        )
        if not success:
            return False, error or "Failed to send verification email."

        return True, "Verification email sent."


email_verification_service = EmailVerificationService()
