"""Twilio WhatsApp template delivery for platform lead alerts."""

import json
import logging

import httpx

from shared.config import settings

logger = logging.getLogger(__name__)
HTTP_TIMEOUT_SECONDS = 10.0


class WhatsAppService:
    """Send approved WhatsApp Content templates through Twilio's REST API."""

    @staticmethod
    def is_configured() -> bool:
        """Return whether the Twilio sender, template, and credentials exist."""
        return bool(
            settings.twilio_account_sid
            and settings.twilio_auth_token
            and settings.twilio_whatsapp_from_number
            and settings.twilio_whatsapp_content_sid
        )

    async def send_template_message(
        self, recipient: str, variables: dict[str, str]
    ) -> bool:
        """Send a pre-approved template without logging its content or recipient."""
        if not self.is_configured():
            return False

        account_sid = settings.twilio_account_sid
        auth_token = settings.twilio_auth_token
        sender = settings.twilio_whatsapp_from_number or ""
        content_sid = settings.twilio_whatsapp_content_sid
        assert account_sid and auth_token and content_sid
        from_address = sender if sender.startswith("whatsapp:") else f"whatsapp:{sender}"
        to_address = (
            recipient if recipient.startswith("whatsapp:") else f"whatsapp:{recipient}"
        )
        url = (
            "https://api.twilio.com/2010-04-01/Accounts/"
            f"{account_sid}/Messages.json"
        )
        try:
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS) as client:
                response = await client.post(
                    url,
                    data={
                        "From": from_address,
                        "To": to_address,
                        "ContentSid": content_sid,
                        "ContentVariables": json.dumps(variables, ensure_ascii=False),
                    },
                    auth=(account_sid, auth_token),
                )
            if response.status_code not in {200, 201}:
                logger.warning(
                    "Twilio WhatsApp template send failed: status=%s",
                    response.status_code,
                )
                return False
            return True
        except Exception as exc:
            logger.warning("Twilio WhatsApp send failed (%s)", type(exc).__name__)
            return False


whatsapp_service = WhatsAppService()
