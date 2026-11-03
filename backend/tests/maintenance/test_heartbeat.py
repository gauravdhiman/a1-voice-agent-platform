"""Independent dead-man signal security and failure handling."""

from unittest.mock import MagicMock, patch

import pytest
from src.maintenance.heartbeat import Heartbeat


@pytest.mark.parametrize(
    "url",
    ["http://example.com/key", "https://u:p@example.com", "https://example.com/#x"],
)
def test_invalid_heartbeat_url_fails_closed(url):
    with pytest.raises(ValueError):
        Heartbeat(url)


@pytest.mark.asyncio
async def test_heartbeat_posts_and_does_not_disclose_url_on_failure():
    connection = MagicMock()
    connection.getresponse.return_value.status = 500
    with patch(
        "src.maintenance.heartbeat.http.client.HTTPSConnection", return_value=connection
    ):
        with pytest.raises(RuntimeError) as error:
            await Heartbeat("https://example.com/private-key").send()
    assert "private-key" not in str(error.value)
    connection.request.assert_called_once_with("POST", "/private-key", body=b"")
    connection.close.assert_called_once()
