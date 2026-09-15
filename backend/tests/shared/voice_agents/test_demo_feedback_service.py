"""Tests for PII-free public demo rating storage."""

from unittest.mock import Mock

import pytest

from shared.voice_agents.demo_feedback_service import DemoFeedbackService


def _mock_client() -> Mock:
    """Build a chainable Supabase-style mock client."""
    table = Mock()
    table.upsert.return_value = table
    table.insert.return_value = table
    table.select.return_value = table
    table.order.return_value = table
    table.limit.return_value = table
    table.execute.return_value = Mock(data=[{"id": "feedback-1"}])
    client = Mock()
    client.table.return_value = table
    return client


@pytest.mark.asyncio
async def test_submit_upserts_one_row_per_session() -> None:
    """Repeat taps from one session update the same row."""
    client = _mock_client()
    service = DemoFeedbackService(client=client)

    assert (
        await service.submit(
            session_id="session-1",
            agent_id="agent-1",
            organization_id="org-1",
            demo_slug="copper-ridge-service-request",
            rating=5,
        )
        is True
    )
    table = client.table.return_value
    table.upsert.assert_called_once()
    row, kwargs = table.upsert.call_args.args[0], table.upsert.call_args.kwargs
    assert row["session_id"] == "session-1"
    assert row["agent_id"] == "agent-1"
    assert row["demo_slug"] == "copper-ridge-service-request"
    assert row["rating"] == 5
    assert kwargs.get("on_conflict") == "session_id"


@pytest.mark.asyncio
@pytest.mark.parametrize("rating", [0, 6, -1, 99])
async def test_submit_rejects_out_of_range_ratings(rating: int) -> None:
    """Scores outside 1-5 never reach storage."""
    client = _mock_client()
    service = DemoFeedbackService(client=client)

    assert (
        await service.submit(
            session_id="session-1",
            agent_id="agent-1",
            organization_id="org-1",
            demo_slug="copper-ridge-service-request",
            rating=rating,
        )
        is False
    )
    client.table.assert_not_called()


@pytest.mark.asyncio
async def test_submit_returns_false_without_a_client() -> None:
    """Missing service-role configuration fails closed."""
    service = DemoFeedbackService(client=None)
    service._client = Mock(return_value=None)  # type: ignore[method-assign]

    assert (
        await service.submit(
            session_id="session-1",
            agent_id="agent-1",
            organization_id="org-1",
            demo_slug="copper-ridge-service-request",
            rating=4,
        )
        is False
    )


@pytest.mark.asyncio
async def test_summary_aggregates_counts_and_averages() -> None:
    """Platform admins see per-demo counts and average scores."""
    client = _mock_client()
    table = client.table.return_value
    table.execute.return_value = Mock(
        data=[
            {"demo_slug": "copper-ridge-service-request", "rating": 5},
            {"demo_slug": "copper-ridge-service-request", "rating": 3},
            {"demo_slug": "pleasant-pediatric-appointments", "rating": 4},
            {"demo_slug": "", "rating": 5},
            {"demo_slug": "broken", "rating": "high"},
        ]
    )
    service = DemoFeedbackService(client=client)

    summary = await service.summary()

    assert [(item.demo_slug, item.count) for item in summary] == [
        ("copper-ridge-service-request", 2),
        ("pleasant-pediatric-appointments", 1),
    ]
    assert summary[0].average_rating == 4.0
    assert summary[1].average_rating == 4.0


@pytest.mark.asyncio
async def test_recent_maps_rows_and_skips_malformed() -> None:
    """Malformed rows never break the admin listing."""
    client = _mock_client()
    table = client.table.return_value
    table.execute.return_value = Mock(
        data=[
            {
                "id": "feedback-1",
                "session_id": "session-1",
                "agent_id": "agent-1",
                "organization_id": "org-1",
                "demo_slug": "copper-ridge-service-request",
                "rating": 5,
                "created_at": "2026-09-14T10:00:00Z",
            },
            {"id": "broken", "rating": "high"},
        ]
    )
    service = DemoFeedbackService(client=client)

    records = await service.recent(limit=10)

    assert len(records) == 1
    assert records[0].demo_slug == "copper-ridge-service-request"
    assert records[0].rating == 5
