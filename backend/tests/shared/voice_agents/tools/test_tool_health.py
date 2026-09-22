"""Tests for attachment configuration health (tool cards stay honest)."""

from shared.voice_agents.tool_health import check_tool_configuration


class TestCheckToolConfiguration:
    def test_sheets_missing_destination_is_flagged(self) -> None:
        """Every generic Sheets attachment must name its destination."""
        assert check_tool_configuration(
            "Google_Sheets",
            {
                "spreadsheet_id": "",
                "default_range": "Lead submissions!A1:L1000",
                "header_range": "Lead submissions!A1:L1",
            },
        ) == ["spreadsheet destination is not set", "agent fields are not set"]

    def test_sheets_complete_config_is_clean(self) -> None:
        """A pasted spreadsheet ID clears the card."""
        assert (
            check_tool_configuration(
                "Google_Sheets",
                {
                    "spreadsheet_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
                    "agent_columns": "Customer name, Items",
                },
            )
            == []
        )

    def test_sheets_full_url_is_accepted_like_the_runtime(self) -> None:
        """The field invites full URLs and the service extracts them."""
        assert (
            check_tool_configuration(
                "Google_Sheets",
                {
                    "spreadsheet_id": (
                        "https://docs.google.com/spreadsheets/d/"
                        "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/edit"
                    ),
                    "agent_columns": "Customer name, Items",
                },
            )
            == []
        )

    def test_resend_reports_every_gap(self) -> None:
        """Sender and routes are each required for a working attachment."""
        assert check_tool_configuration(
            "Resend_email",
            {"from_email": None, "from_name": None, "routes": []},
        ) == ["sender email is not set", "no email routes are configured"]

    def test_resend_complete_config_is_clean(self) -> None:
        """A sender with one route is ready (auth is reported separately)."""
        assert (
            check_tool_configuration(
                "Resend_email",
                {
                    "from_email": "noreply@example.com",
                    "routes": [
                        {
                            "route_id": "owner",
                            "label": "Owner",
                            "recipients": ["owner@example.com"],
                        }
                    ],
                },
            )
            == []
        )

    def test_invalid_stored_config_is_flagged_not_crashed(self) -> None:
        """Legacy rows that fail validation surface one safe issue."""
        assert check_tool_configuration(
            "Resend_email",
            {"routes": [{"route_id": "NOT A ROUTE", "label": "x", "recipients": []}]},
        ) == ["stored configuration is invalid and must be re-saved"]

    def test_unknown_tool_is_neutral(self) -> None:
        """Unregistered names never red-card a card (MCP rows, future tools)."""
        assert check_tool_configuration("Some_Future_Tool", {}) == []
        assert check_tool_configuration(None, {}) == []

    def test_tools_without_requirements_default_clean(self) -> None:
        """Gmail needs only credentials, which auth status already covers."""
        assert check_tool_configuration("Gmail", {}) == []

    def test_full_native_tool_audit_matrix(self) -> None:
        """Every native tool has a deliberate health verdict for empty config.

        This is the systematic audit: adding a tool with required
        attachment fields must add an override (and a row here), or the
        card silently stays green like Jordan's Sheets card did.
        """
        assert check_tool_configuration("CalCom", {}) == [
            "default event type is not set"
        ]
        assert check_tool_configuration("Google_calendar", {}) == []
        assert check_tool_configuration("Google_calendar_appointment", {}) == []
        assert check_tool_configuration("Google_Sheets", {}) == [
            "spreadsheet destination is not set",
            "agent fields are not set",
        ]
        assert check_tool_configuration("HubSpot_lead_capture", {}) == []

    def test_callback_reports_every_gap(self) -> None:
        """Owner callback needs a sender and at least one owner route."""
        assert check_tool_configuration(
            "Callback_request",
            {"from_email": None, "from_name": None, "routes": []},
        ) == ["sender email is not set", "no owner routes are configured"]
