"""Tests for org-admin call-recording deletion.

Covers the RBAC gate, tombstone semantics (artifact row kept, audio removed),
batch behavior, and the storage-failure path where the DB must NOT be
tombstoned when the object could not be deleted.
"""

from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from src.call_artifacts import routes


def _profile(*roles: str):
    """Build a minimal profile with role names for access tests."""
    profile = Mock()
    profile.has_role.side_effect = lambda role, organization_id=None: (
        role in roles
    )
    # Role-only profiles hold no explicit permission grants.
    profile.has_permission.side_effect = (
        lambda name, organization_id=None: False
    )
    return profile


def _permission_profile(*grants: str):
    """Build a profile whose has_permission mirrors org-scoped grants."""
    profile = Mock()
    profile.has_role.return_value = False

    def _has_permission(name: str, organization_id: str | None = None) -> bool:
        return name in grants

    profile.has_permission.side_effect = _has_permission
    return profile


def _completed_artifact(org_id, call_log_id=None):
    """Shape of a completed recording row as loaded by get_recording."""
    return {
        "id": str(uuid4()),
        "call_log_id": str(call_log_id or uuid4()),
        "organization_id": str(org_id),
        "status": "completed",
        "storage_path": "org/call/recording.wav",
        "mime_type": "audio/wav",
        "metadata": {},
    }


# --------------------------------------------------------------------------
# Permission gate: delete_recording_access
# --------------------------------------------------------------------------


def test_platform_admin_passes_delete_gate():
    assert routes._check_delete_access(_profile("platform_admin"), uuid4()) is None


def test_org_admin_with_permission_passes_delete_gate():
    org_id = uuid4()
    profile = _permission_profile("call_log:delete")
    # has_role returns False; the permission path must grant access.
    assert routes._check_delete_access(profile, org_id) is None


def test_org_admin_without_delete_permission_is_denied():
    with pytest.raises(HTTPException) as exc_info:
        routes._check_delete_access(
            _permission_profile("call_log:read"), uuid4()
        )
    assert exc_info.value.status_code == 403


def test_regular_user_is_denied_delete_gate():
    with pytest.raises(HTTPException) as exc_info:
        routes._check_delete_access(_profile("regular_user"), uuid4())
    assert exc_info.value.status_code == 403


# --------------------------------------------------------------------------
# Single recording deletion route
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_single_removes_object_and_tombstones_row(monkeypatch):
    """Successful delete removes the object then marks status='deleted'."""
    call_id = uuid4()
    org_id = uuid4()
    artifact = _completed_artifact(org_id, call_id)
    admin = _permission_profile("call_log:delete")

    monkeypatch.setattr(
        routes.call_artifact_service,
        "get_recording",
        AsyncMock(return_value=(artifact, None)),
    )
    storage = Mock()
    storage.delete_object = AsyncMock(return_value=None)
    monkeypatch.setattr(routes, "get_recording_storage", lambda: storage)
    mark_deleted = AsyncMock(return_value=(True, None))
    monkeypatch.setattr(
        routes.call_artifact_service, "mark_recording_deleted", mark_deleted
    )

    response = await routes.delete_call_recording(call_id, (uuid4(), admin))

    assert response.status_code == 200
    body = response.body.decode() if isinstance(response.body, bytes) else "{}"
    assert '"status": "deleted"' in body or '"deleted": true' in body
    storage.delete_object.assert_awaited_once_with(artifact["storage_path"])
    mark_deleted.assert_awaited_once()

@pytest.mark.asyncio
async def test_delete_single_404_when_no_recording(monkeypatch):
    """A missing/unready recording yields 404 without touching storage."""
    admin = _permission_profile("call_log:delete")
    monkeypatch.setattr(
        routes.call_artifact_service,
        "get_recording",
        AsyncMock(return_value=(None, "Recording not found")),
    )
    storage = Mock()
    storage.delete_object = AsyncMock()
    monkeypatch.setattr(routes, "get_recording_storage", lambda: storage)

    with pytest.raises(HTTPException) as exc_info:
        await routes.delete_call_recording(uuid4(), (uuid4(), admin))

    assert exc_info.value.status_code == 404
    storage.delete_object.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_single_storage_failure_keeps_row_playable(monkeypatch):
    """If storage delete fails, the artifact stays completed and 502 returned.

    This ordering guarantees a user-visible failure never leaves a recording
    that is gone from storage but still advertised as available.
    """
    org_id = uuid4()
    artifact = _completed_artifact(org_id)
    admin = _permission_profile("call_log:delete")

    monkeypatch.setattr(
        routes.call_artifact_service,
        "get_recording",
        AsyncMock(return_value=(artifact, None)),
    )
    storage = Mock()
    storage.delete_object = AsyncMock(side_effect=RuntimeError("R2 down"))
    monkeypatch.setattr(routes, "get_recording_storage", lambda: storage)
    mark_deleted = AsyncMock()
    monkeypatch.setattr(
        routes.call_artifact_service, "mark_recording_deleted", mark_deleted
    )

    with pytest.raises(HTTPException) as exc_info:
        await routes.delete_call_recording(uuid4(), (uuid4(), admin))

    assert exc_info.value.status_code == 502
    mark_deleted.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_single_r2_backend_checks_existence(monkeypatch):
    """R2 flow verifies object existence before deleting (parity with GET)."""
    org_id = uuid4()
    artifact = _completed_artifact(org_id)
    admin = _permission_profile("call_log:delete")

    monkeypatch.setattr(
        routes.call_artifact_service,
        "get_recording",
        AsyncMock(return_value=(artifact, None)),
    )
    storage = Mock()
    storage.object_exists = AsyncMock(return_value=False)
    storage.delete_object = AsyncMock()
    monkeypatch.setattr(routes, "get_recording_storage", lambda: storage)
    monkeypatch.setattr(routes.settings, "recording_storage_backend", "r2")
    mark_missing = AsyncMock(return_value=True)
    monkeypatch.setattr(
        routes.call_artifact_service, "mark_recording_missing", mark_missing
    )

    with pytest.raises(HTTPException) as exc_info:
        await routes.delete_call_recording(uuid4(), (uuid4(), admin))

    assert exc_info.value.status_code == 410
    storage.object_exists.assert_awaited_once_with(artifact["storage_path"])
    storage.delete_object.assert_not_awaited()
    mark_missing.assert_awaited_once_with(artifact)


# --------------------------------------------------------------------------
# Batch recording deletion route
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_batch_delete_reports_per_item_outcomes(monkeypatch):
    """Batch returns per-item results including cross-tenant skips."""
    org_a = uuid4()
    org_b = uuid4()  # different tenant than the caller's checked org
    artifact_a = _completed_artifact(org_a)
    artifact_b = _completed_artifact(org_b)
    caller_org = org_a
    admin = Mock()

    async def fake_get_recording(call_log_id):
        if str(call_log_id) == "a-uuid":
            return artifact_a, None
        if str(call_log_id) == "b-uuid":
            return artifact_b, None
        return None, "Recording not found"

    # Route contract: batch endpoint receives explicit ids + caller org.
    storage = Mock()
    storage.delete_object = AsyncMock(return_value=None)
    monkeypatch.setattr(routes, "get_recording_storage", lambda: storage)

    from src.call_artifacts.models import RecordingBatchDeleteRequest

    request = RecordingBatchDeleteRequest(
        call_log_ids=["a-uuid", "b-uuid", "missing-uuid"],
        organization_id=caller_org,
    )
    result = await routes.batch_delete_recordings(request, (uuid4(), admin))
    statuses = {item.call_log_id: item.status for item in result.items}
    assert statuses["missing-uuid"] == "not_found"
    # Cross-tenant artifact never reached storage.
    deleted_keys = [c.args[0] for c in storage.delete_object.await_args_list]
    assert artifact_b["storage_path"] not in deleted_keys


@pytest.mark.asyncio
async def test_batch_delete_rejects_empty_and_large_batches(monkeypatch):
    """Validation rejects empty lists and batches over the cap."""
    from src.call_artifacts.models import RecordingBatchDeleteRequest

    with pytest.raises(ValueError):
        RecordingBatchDeleteRequest(call_log_ids=[], organization_id=uuid4())

    with pytest.raises(ValueError):
        RecordingBatchDeleteRequest(
            call_log_ids=[f"id-{i}" for i in range(101)],
            organization_id=uuid4(),
        )


# --------------------------------------------------------------------------
# Service: mark_recording_deleted tombstone
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mark_recording_deleted_sets_status_and_audit_metadata(monkeypatch):
    """Tombstone keeps the row but flips status and records who/when/why."""
    captured = {}

    class FakeTable:
        def update(self, payload):
            captured["payload"] = payload
            return self

        def eq(self, *args, **kwargs):
            captured["eq"] = args
            return self

        def execute(self):
            captured["executed"] = True
            return Mock(data=[{"id": "artifact-1"}])

    service = routes.call_artifact_service
    monkeypatch.setattr(
        type(service),
        "supabase",
        property(lambda self: Mock(table=lambda name: FakeTable())),
    )

    artifact = {"id": "artifact-1", "metadata": {"existing": True}}
    ok, error = await service.mark_recording_deleted(
        artifact,
        deleted_by="user-123",
        reason="user_requested",
    )

    assert ok is True and error is None
    payload = captured["payload"]
    assert payload["status"] == "deleted"
    meta = payload["metadata"]
    assert meta["existing"] is True  # existing metadata preserved
    assert meta["deletion"]["reason"] == "user_requested"
    assert meta["deletion"]["deleted_by"] == "user-123"
    assert "deleted_at" in meta["deletion"]
