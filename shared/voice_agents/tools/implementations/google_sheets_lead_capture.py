"""Focused Google Sheets lead-capture tool for the public service demo."""

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from pydantic import Field

from shared.voice_agents.tools.base.auth_config import GoogleAuthConfig
from shared.voice_agents.tools.base.base_tool import (
    BaseConfig,
    BaseSensitiveConfig,
    BaseTool,
    ToolMetadata,
)
from shared.voice_agents.tools.base.tool_context import ToolContext
from shared.voice_agents.tools.google_sheets_lead_service import (
    _SPREADSHEET_ID_PATTERN,
    GoogleSheetsLeadService,
)


class GoogleSheetsLeadCaptureTool(BaseTool):
    """Capture one confirmed service inquiry in a configured Google Sheet.

    This is intentionally separate from the general-purpose ``Google_Sheets``
    tool. The public demo gives the model one typed business action; it never
    needs to choose a spreadsheet, construct arbitrary row arrays, or browse
    the organization's other spreadsheets.
    """

    class AuthConfig(GoogleAuthConfig):
        """OAuth scopes used by the existing Google Sheets connection flow."""

        scopes: list[str] = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive.file",
            "https://www.googleapis.com/auth/drive.metadata.readonly",
        ]
        auth_url: str = "https://accounts.google.com/o/oauth2/v2/auth"
        token_url: str = "https://oauth2.googleapis.com/token"

    class Config(BaseConfig):
        """Destination policy for one lead-capture workflow."""

        spreadsheet_id: str = Field(
            default="",
            description=(
                "Required. Paste the full Google Sheets URL or spreadsheet ID. "
                "The Google account connected above must have Editor access; "
                "do not make the sheet public. The agent must never ask the "
                "caller for this value."
            ),
        )
        append_range: str = Field(
            default="Lead submissions!A:L",
            max_length=200,
            description=(
                "A1 range covering all 12 lead columns. Use "
                "'Lead submissions!A:L' exactly unless you intentionally use "
                "a different tab and column layout. The tab name must match "
                "the spreadsheet."
            ),
        )
        dedupe_range: str = Field(
            default="Lead submissions!A:A",
            max_length=200,
            description=(
                "A1 range for the Submission ID column used to recognize a "
                "same-session retry. Use 'Lead submissions!A:A' with the "
                "standard header in cell A1."
            ),
        )
        lead_source: str = Field(
            default="24x7 AI public demo",
            max_length=120,
            description=(
                "Free-form label written into column C for filtering and "
                "reporting. It does not need to match another system; keep "
                "'24x7 AI public demo' for this showcase."
            ),
        )

    class SensitiveConfig(BaseSensitiveConfig):
        """OAuth tokens stored encrypted by the platform."""

        access_token: str = ""
        refresh_token: Optional[str] = None
        token_expiry: Optional[str] = None

    @property
    def metadata(self) -> ToolMetadata:
        """Return the focused platform catalog contract."""
        return ToolMetadata(
            name="Google_Sheets_lead_capture",
            description=(
                "Capture a confirmed home-service inquiry as one complete row "
                "in a configured Google Sheet."
            ),
            requires_auth=True,
            auth_type="oauth2",
            auth_config=self.AuthConfig().model_dump(),
            config_schema=self.Config.model_json_schema(),
        )

    def check_configuration(self) -> list[str]:
        """Flag a missing spreadsheet destination before any call runs.

        Mirrors the runtime exactly: the service accepts a full Sheets URL
        or a bare id, so the check extracts first and validates second.
        Checking the raw value would red-card valid URL pastes.
        """
        raw = (self.config.spreadsheet_id or "").strip()
        extracted = GoogleSheetsLeadService.extract_spreadsheet_id(raw)
        if not _SPREADSHEET_ID_PATTERN.fullmatch(extracted):
            return ["spreadsheet destination is not set"]
        return []

    def _service(self) -> GoogleSheetsLeadService:
        """Build the provider service from the agent's saved connection."""
        return GoogleSheetsLeadService(
            access_token=self.sensitive_config.access_token,
            spreadsheet_id=self.config.spreadsheet_id,
            append_range=self.config.append_range,
            dedupe_range=self.config.dedupe_range,
            lead_source=self.config.lead_source,
        )

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
        """Save a complete, caller-confirmed service inquiry to Google Sheets.

        Collect the caller name, service needed, concise issue summary, and at
        least one follow-up channel (email or phone). Capture the address,
        urgency, and callback window when available. Read every detail back and
        set ``user_confirmed`` to true only after the caller approves it. Call
        this function exactly once after confirmation; a same-session retry is
        deduplicated by the submission id. Never use it for a hypothetical or
        unconfirmed inquiry, and never claim success unless the result status
        is ``created``. The agent does not need to know the spreadsheet id or
        construct row values.
        """
        if not user_confirmed:
            return {
                "status": "confirmation_required",
                "provider": "google_sheets",
                "message": "Ask the caller to confirm the full service inquiry before saving it.",
                "next_action": "ask_for_confirmation",
            }

        result = await self._service().capture_lead(
            caller_name=caller_name,
            caller_email=caller_email,
            caller_phone=caller_phone,
            service_needed=service_needed,
            issue_summary=issue_summary,
            property_address=property_address,
            urgency=urgency,
            preferred_callback_window=preferred_callback_window,
            submission_id=(context.session_id or str(uuid4())),
            captured_at=context.current_time or datetime.now(timezone.utc),
        )
        return result


__all__ = ["GoogleSheetsLeadCaptureTool"]
