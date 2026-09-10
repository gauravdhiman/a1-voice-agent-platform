"""Backend-owned password reset (Epic E hardening).

Replaces the previous frontend-only reset path with a rate-limited,
audited server flow:

1. ``POST /api/v1/auth/password-reset`` accepts any email and always
   returns the same safe message (no account oracle).
2. When the account exists, a Supabase recovery link is generated with
   ``redirect_to`` pointed at the frontend reset page, and delivered
   through the existing ``user.password_reset`` Resend template.
3. Every attempt is audit-logged server-side.
"""

from __future__ import annotations

import logging
from typing import Optional, Tuple
from uuid import UUID

from shared.config import settings, supabase_config
from src.notifications.models import SendNotificationRequest
from src.notifications.service import notification_service

logger = logging.getLogger(__name__)

SAFE_RESET_MESSAGE = "If an account exists for that email, a reset link is on its way."
RESET_LINK_EXPIRY_HOURS = "1"


class PasswordResetService:
    """Generate recovery links and deliver them through Resend."""

    @property
    def supabase(self):
        """Return the service-role client or raise when unconfigured."""
        if not supabase_config.is_configured():
            raise ValueError("Supabase is not configured")
        client = supabase_config.service_client
        if client is None:
            raise ValueError("Supabase service client is not available")
        return client

    async def request_reset(self, email: str) -> Tuple[bool, Optional[str]]:
        """Send a reset email when the account exists.

        Args:
            email: Caller-supplied email address.

        Returns:
            Tuple of (sent, error). ``sent`` is True only when an email
            was actually dispatched; callers must still return the safe
            message either way.
        """
        from src.auth.service import auth_service

        normalized = email.strip()
        user = await auth_service._find_auth_user_by_email(normalized)
        if user is None:
            return False, None

        try:
            link_response = self.supabase.auth.admin.generate_link(
                {
                    "type": "recovery",
                    "email": normalized,
                    "options": {
                        "redirect_to": (
                            f"{settings.app_base_url.rstrip('/')}"
                            "/auth/reset-password"
                        )
                    },
                }
            )
        except Exception:
            logger.error("Recovery link generation failed", exc_info=True)
            return False, "Could not create a reset link. Please try again."

        properties = getattr(link_response, "properties", None)
        action_link = getattr(properties, "action_link", None)
        if not action_link:
            logger.error("Recovery link response had no action link")
            return False, "Could not create a reset link. Please try again."

        metadata = getattr(user, "user_metadata", None) or {}
        first_name = metadata.get("first_name") or "there"
        request = SendNotificationRequest(
            event_key="user.password_reset",
            recipient_email=normalized,
            recipient_name=first_name,
            user_id=UUID(str(user.id)),
            template_variables={
                "user_name": first_name,
                "reset_url": action_link,
                "expiry_hours": RESET_LINK_EXPIRY_HOURS,
                "app_name": settings.app_name,
            },
            template_id=None,
        )
        response = await notification_service.send_notification(request)
        if not response.success:
            return False, response.message or "Could not send the reset email."
        return True, None


password_reset_service = PasswordResetService()
