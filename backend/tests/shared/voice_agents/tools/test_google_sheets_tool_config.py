"""Contracts for Google Sheets attachment setup metadata."""

from shared.voice_agents.tools.implementations.google_sheets import GoogleSheetsTool


def test_google_sheets_config_preserves_discovered_tab_id() -> None:
    """The selected tab identity must persist in saved attachment config."""
    config = GoogleSheetsTool.Config.model_validate(
        {
            "spreadsheet_id": "sheet-id-123456",
            "selected_sheet_id": "42",
        }
    )

    assert config.selected_sheet_id == "42"
    assert (
        "selected_sheet_id" in GoogleSheetsTool.Config.model_json_schema()["properties"]
    )
