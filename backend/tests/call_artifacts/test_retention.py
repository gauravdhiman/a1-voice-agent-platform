"""Retention enforcement and retry-safe provider deletion."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from src.call_artifacts import retention
from src.call_artifacts.service import CallArtifactService


@pytest.mark.parametrize(
    "expiry,expired",
    [
        (None, False),
        ("invalid", True),
        ("2020-01-01T00:00:00", True),
        ("2020-01-01T00:00:00Z", True),
        ("2099-01-01T00:00:00+00:00", False),
    ],
)
def test_playback_retention_boundary(expiry, expired):
    assert retention.recording_expired({"retention_expires_at": expiry}) is expired


def _database(monkeypatch, rows):
    query = MagicMock()
    for method in ["select", "eq", "lte", "order", "limit", "update"]:
        getattr(query, method).return_value = query
    query.execute.return_value = SimpleNamespace(data=rows)
    client = MagicMock()
    client.table.return_value = query
    monkeypatch.setattr(
        retention, "supabase_config", SimpleNamespace(service_client=client)
    )
    return query, client


@pytest.mark.asyncio
async def test_expired_recording_cannot_be_played_before_cleanup(monkeypatch):
    row = {
        "status": "completed",
        "storage_path": "private.wav",
        "retention_expires_at": "2020-01-01T00:00:00Z",
    }
    query, client = _database(monkeypatch, [row])
    monkeypatch.setattr(CallArtifactService, "supabase", property(lambda _: client))
    result, error = await CallArtifactService().get_recording(uuid4())
    assert result is None
    assert "expired" in error


@pytest.mark.asyncio
async def test_retention_deletes_before_tombstoning_and_is_bounded(monkeypatch):
    row = {
        "id": str(uuid4()),
        "storage_path": "private.wav",
        "metadata": {"keep": True},
        "retention_expires_at": (
            (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        ),
    }
    query, _ = _database(monkeypatch, [row])
    storage = SimpleNamespace(delete_object=AsyncMock())
    monkeypatch.setattr(retention, "get_recording_storage", lambda: storage)
    assert await retention.remove_expired_recordings(10000) == 1
    storage.delete_object.assert_awaited_once_with("private.wav")
    query.limit.assert_called_once_with(100)
    payload = query.update.call_args.args[0]
    assert payload["status"] == "deleted"
    assert payload["metadata"]["keep"] is True
    assert payload["metadata"]["deletion"]["reason"] == "retention_expired"


@pytest.mark.asyncio
async def test_provider_failure_leaves_artifact_retryable(monkeypatch):
    query, _ = _database(
        monkeypatch,
        [
            {
                "id": str(uuid4()),
                "storage_path": "private.wav",
                "retention_expires_at": "2020-01-01T00:00:00Z",
            }
        ],
    )
    storage = SimpleNamespace(delete_object=AsyncMock(side_effect=TimeoutError))
    monkeypatch.setattr(retention, "get_recording_storage", lambda: storage)
    assert await retention.remove_expired_recordings() == 0
    query.update.assert_not_called()


@pytest.mark.asyncio
async def test_database_failure_retries_idempotent_object_delete(monkeypatch):
    row = {
        "id": str(uuid4()),
        "storage_path": "private.wav",
        "retention_expires_at": "2020-01-01T00:00:00Z",
    }
    query, _ = _database(monkeypatch, [row])
    query.execute.side_effect = [
        SimpleNamespace(data=[row]),
        TimeoutError(),
        SimpleNamespace(data=[row]),
        SimpleNamespace(data=[row]),
    ]
    storage = SimpleNamespace(delete_object=AsyncMock())
    monkeypatch.setattr(retention, "get_recording_storage", lambda: storage)
    assert await retention.remove_expired_recordings() == 0
    assert await retention.remove_expired_recordings() == 1
    assert storage.delete_object.await_count == 2
