"""Security regression tests for native Google Sheets OAuth handling."""

import logging
from unittest.mock import AsyncMock, Mock

import httpx
import pytest

from shared.voice_agents.tools.implementations.google_sheets import GoogleSheetsTool


@pytest.mark.asyncio
async def test_list_spreadsheets_never_logs_access_token(monkeypatch, caplog):
    """Native tool diagnostics must not expose even an access-token prefix."""
    access_token = "native-access-token-must-not-appear-in-logs"
    response = Mock()
    response.json.return_value = {"files": []}
    response.raise_for_status.return_value = None

    http_client = AsyncMock()
    http_client.get.return_value = response
    http_client.__aenter__.return_value = http_client
    http_client.__aexit__.return_value = None
    monkeypatch.setattr(
        "shared.voice_agents.tools.implementations.google_sheets.httpx.AsyncClient",
        lambda: http_client,
    )

    tool = GoogleSheetsTool(sensitive_config={"access_token": access_token})
    with caplog.at_level(logging.INFO):
        result = await tool.list_user_spreadsheets(Mock())

    assert result["total_spreadsheets"] == 0
    assert access_token not in caplog.text
    assert "access_token prefix" not in caplog.text


def test_google_sheets_api_errors_do_not_echo_grant_material(caplog):
    """Provider error bodies and query strings cannot expose OAuth grants."""
    access_token = "oauth-access-token-must-not-escape"
    request = httpx.Request(
        "GET",
        f"https://www.googleapis.com/drive/v3/files?access_token={access_token}",
    )
    response = httpx.Response(
        403,
        request=request,
        json={"error": {"message": f"invalid access_token={access_token}"}},
    )
    error = httpx.HTTPStatusError(
        "provider rejected request", request=request, response=response
    )
    tool = GoogleSheetsTool(sensitive_config={"access_token": access_token})

    with caplog.at_level(logging.ERROR):
        result = tool._handle_api_error(error, "list_user_spreadsheets")

    assert access_token not in caplog.text
    assert access_token not in str(result)
