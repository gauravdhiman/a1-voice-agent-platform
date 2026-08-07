"""
Platform admin alerts for new signups and invitation joins.
"""

import logging
from datetime import datetime, timezone
from typing import Literal, Optional
from uuid import UUID

from .platform_settings_service import platform_notification_settings_service
from .telegram_service import telegram_service

logger = logging.getLogger(__name__)

SignupMethod = Literal["email", "google", "linkedin", "invitation"]


class SignupNotifier:
    """Send Telegram alerts to platform admins on signup events."""

    async def notify_new_user(
        self,
        *,
        email: str,
        user_id: UUID,
        method: SignupMethod,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        organization_name: Optional[str] = None,
        is_new_user: bool = True,
    ) -> None:
        """Notify platform admin about a signup or invitation join."""
        bot_token, chat_id, enabled = (
            await platform_notification_settings_service.get_telegram_credentials()
        )
        if not enabled or not bot_token or not chat_id:
            logger.debug("Telegram notifications disabled or not configured")
            return

        display_name = " ".join(
            part for part in [first_name, last_name] if part
        ).strip() or "—"
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        if is_new_user:
            headline = "🆕 New user signup"
        else:
            headline = "👤 User joined via invitation"

        lines = [
            headline,
            f"Email: {email}",
            f"Name: {display_name}",
            f"Method: {method}",
            f"User ID: {user_id}",
        ]
        if organization_name:
            lines.append(f"Organization: {organization_name}")
        lines.append(f"Time: {timestamp}")

        text = "\n".join(lines)
        sent = await telegram_service.send_message(bot_token, chat_id, text)
        if not sent:
            logger.warning(
                "Failed to send Telegram signup notification for user %s", user_id
            )


signup_notifier = SignupNotifier()
