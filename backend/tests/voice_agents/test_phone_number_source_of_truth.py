"""Tests for table-backed phone-number values returned with voice agents."""

from unittest.mock import AsyncMock, Mock, PropertyMock, patch
from uuid import UUID

import pytest

from shared.voice_agents.service import VoiceAgentService, merge_phone_number_mappings


def test_merge_phone_number_mappings_replaces_legacy_values_with_assigned_rows():
    """An assigned table row is the value exposed to agent list consumers."""
    agents = [
        {"id": "agent-1", "phone_number": "+14155550100"},
        {"id": "agent-2", "phone_number": "+14155550200"},
    ]
    phone_numbers = [{"assigned_agent_id": "agent-1", "phone_number": "+14155550300"}]

    assert merge_phone_number_mappings(agents, phone_numbers) == [
        {"id": "agent-1", "phone_number": "+14155550300"},
        {"id": "agent-2", "phone_number": None},
    ]


def test_merge_phone_number_mappings_ignores_unassigned_rows():
    """Unassigned organization numbers must not appear on an agent."""
    agents = [{"id": "agent-1", "phone_number": "+14155550100"}]

    assert merge_phone_number_mappings(
        agents,
        [{"assigned_agent_id": None, "phone_number": "+14155550300"}],
    ) == [{"id": "agent-1", "phone_number": None}]


def test_service_mapping_loader_handles_empty_and_idless_rows():
    """The loader handles empty query results without touching Supabase."""
    service = VoiceAgentService()

    assert service._with_phone_number_mappings([]) == []
    assert service._with_phone_number_mappings([{"phone_number": "+14155550100"}]) == [
        {"phone_number": None}
    ]


def test_service_mapping_loader_reads_table_assignments():
    """The loader replaces each agent's legacy value with its assignment."""
    service = VoiceAgentService()
    query = Mock()
    query.select.return_value = query
    query.in_.return_value = query
    query.execute.return_value = Mock(
        data=[{"assigned_agent_id": "agent-1", "phone_number": "+14155550300"}]
    )
    client = Mock()
    client.table.return_value = query

    with patch.object(
        type(service.supabase_config),
        "client",
        new_callable=PropertyMock,
        return_value=client,
    ):
        result = service._with_phone_number_mappings(
            [{"id": "agent-1", "phone_number": "+14155550100"}]
        )

    assert result == [{"id": "agent-1", "phone_number": "+14155550300"}]


def test_service_mapping_loader_falls_back_if_table_lookup_fails():
    """A temporary assignment-query failure preserves read availability."""
    service = VoiceAgentService()
    client = Mock()
    client.table.side_effect = RuntimeError("database unavailable")

    legacy_rows = [{"id": "agent-1", "phone_number": "+14155550100"}]
    with patch.object(
        type(service.supabase_config),
        "client",
        new_callable=PropertyMock,
        return_value=client,
    ):
        assert service._with_phone_number_mappings(legacy_rows) == legacy_rows


@pytest.mark.asyncio
async def test_get_agent_by_phone_reads_phone_numbers_table():
    """The compatibility lookup must not query the legacy agent column."""
    service = VoiceAgentService()
    query = Mock()
    query.select.return_value = query
    query.eq.return_value = query
    query.in_.return_value = query
    query.limit.return_value = query
    query.execute.return_value = Mock(
        data=[{"assigned_agent_id": "00000000-0000-0000-0000-000000000001"}]
    )
    client = Mock()
    client.table.return_value = query
    expected = (Mock(), None)
    get_agent_by_id = AsyncMock(return_value=expected)

    with patch.object(
        type(service.supabase_config),
        "client",
        new_callable=PropertyMock,
        return_value=client,
    ), patch.object(
        service,
        "get_agent_by_id",
        get_agent_by_id,
    ):
        result = await service.get_agent_by_phone("+14155550100")

    assert result == expected
    client.table.assert_called_once_with("phone_numbers")
    get_agent_by_id.assert_awaited_once_with(
        UUID("00000000-0000-0000-0000-000000000001")
    )
