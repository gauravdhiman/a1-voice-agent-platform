"""
Telegram Bot API integration for platform admin alerts.
"""

import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

TELEGRAM_API_BASE = "https://api.telegram.org"
HTTP_TIMEOUT_SECONDS = 10.0


class TelegramService:
    """Send messages to platform admins via Telegram Bot API."""

    async def send_message(
        self,
        bot_token: str,
        chat_id: str,
        text: str,
        *,
        parse_mode: Optional[str] = None,
    ) -> bool:
        """Send a Telegram message. Returns True on success."""
        url = f"{TELEGRAM_API_BASE}/bot{bot_token}/sendMessage"
        payload: dict = {"chat_id": chat_id, "text": text}
        if parse_mode:
            payload["parse_mode"] = parse_mode

        try:
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS) as client:
                response = await client.post(url, json=payload)
                if response.status_code != 200:
                    logger.warning(
                        "Telegram sendMessage failed: status=%s body=%s",
                        response.status_code,
                        response.text[:500],
                    )
                    return False
                body = response.json()
                if not body.get("ok"):
                    logger.warning("Telegram API returned ok=false: %s", body)
                    return False
                return True
        except Exception as exc:
            logger.error("Telegram sendMessage error: %s", exc, exc_info=True)
            return False


telegram_service = TelegramService()
