"""Provider failures leave financial work pending instead of claiming success."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from shared.billing.voice_settlement import settle_voice_call


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "data,expected",
    [
        ({"success": True}, True),
        ({"success": False}, False),
        ({}, False),
        ([], False),
        (None, False),
    ],
)
async def test_atomic_rpc_result_is_verified(data, expected):
    client = Mock()
    client.rpc.return_value.execute.return_value = SimpleNamespace(data=data)
    assert await settle_voice_call(client, "call-test") is expected
    client.rpc.assert_called_once_with(
        "settle_voice_call", {"p_call_log_id": "call-test"}
    )


@pytest.mark.asyncio
async def test_rpc_outage_does_not_discard_pending_work():
    client = Mock()
    client.rpc.return_value.execute.side_effect = TimeoutError(
        "private provider response"
    )
    assert await settle_voice_call(client, "call-test") is False
    client.table.assert_not_called()
