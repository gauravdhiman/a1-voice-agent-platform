"""HubSpot service-inquiry capture tool for voice agents."""

from typing import Any

from pydantic import Field

from shared.voice_agents.tools.base.auth_config import ApiKeyAuthConfig
from shared.voice_agents.tools.base.base_tool import (
    BaseConfig,
    BaseSensitiveConfig,
    BaseTool,
    ToolMetadata,
)
from shared.voice_agents.tools.base.tool_context import ToolContext
from shared.voice_agents.tools.hubspot_lead_service import HubSpotLeadService


class HubspotLeadCaptureTool(BaseTool):
    """Capture a confirmed service inquiry in HubSpot as contact + note."""

    class Config(BaseConfig):
        """Public HubSpot capture policy."""

        api_base_url: str = Field(
            default="https://api.hubapi.com",
            description="HubSpot API base URL; keep the production default unless testing.",
        )
        lead_source: str = Field(
            default="Voice inquiry",
            max_length=120,
            description="Source label written into the associated HubSpot note.",
        )

    class AuthConfig(ApiKeyAuthConfig):
        """HubSpot private-app token presented as an API-key connection."""

        provider: str = "api_key"

    class SensitiveConfig(BaseSensitiveConfig):
        """Encrypted HubSpot private-app token; never exposed to callers."""

        api_key: str = ""
        access_token: str = ""

    @property
    def metadata(self) -> ToolMetadata:
        """Return the platform catalog contract for HubSpot."""
        return ToolMetadata(
            name="HubSpot_lead_capture",
            description=(
                "Capture a confirmed service inquiry in HubSpot as a contact and "
                "an associated note."
            ),
            requires_auth=True,
            auth_type="api_key",
            auth_config=self.AuthConfig().model_dump(),
            config_schema=self.Config.model_json_schema(),
        )

    def _access_token(self, context: ToolContext) -> str:
        """Resolve the encrypted agent-scoped HubSpot connection."""
        token = (
            self.sensitive_config.access_token.strip()
            or self.sensitive_config.api_key.strip()
        )
        return token

    async def capture_lead(
        self,
        context: ToolContext,
        caller_name: str,
        service_needed: str,
        issue_summary: str,
        user_confirmed: bool,
        caller_email: str = "",
        caller_phone: str = "",
        property_address: str = "",
        urgency: str = "",
        preferred_callback_window: str = "",
    ) -> dict[str, Any]:
        """Capture a confirmed home-service inquiry in HubSpot.

        Collect the caller name, service needed, concise issue summary, and at
        least one follow-up channel (email or phone). Address, urgency, and
        callback window are captured when available. Read the complete summary
        back to the caller and set ``user_confirmed`` to true only after they
        approve it. Never call this function for a hypothetical or unconfirmed
        inquiry. A successful result means the HubSpot contact and associated
        note were written; inspect the result before claiming success.
        """
        if not user_confirmed:
            return {
                "status": "confirmation_required",
                "message": "Ask the caller to confirm the full service inquiry before saving it.",
                "next_action": "ask_for_confirmation",
            }
        access_token = self._access_token(context)
        if not access_token:
            return {
                "status": "not_configured",
                "message": "HubSpot is not connected for this agent.",
                "next_action": "reauthorize",
                "error": {
                    "code": "authentication_required",
                    "message": "HubSpot is not connected for this agent.",
                    "next_action": "reauthorize",
                    "retryable": False,
                },
            }

        result = await HubSpotLeadService(
            access_token=access_token,
            base_url=self.config.api_base_url,
            lead_source=self.config.lead_source,
        ).capture_lead(
            caller_name=caller_name,
            caller_email=caller_email,
            caller_phone=caller_phone,
            service_needed=service_needed,
            issue_summary=issue_summary,
            property_address=property_address,
            urgency=urgency,
            preferred_callback_window=preferred_callback_window,
        )
        return result


__all__ = ["HubspotLeadCaptureTool"]
