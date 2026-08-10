"""Tests for authorized call recording access."""

from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from src.call_artifacts import routes
from src.call_artifacts.routes import _check_artifact_access


def _profile(*roles: str):
    """Build a minimal profile with role names for access tests."""
    from unittest.mock import Mock

    profile = Mock()
    profile.has_role.side_effect = lambda role, organization_id=None: role in roles
    return profile


def test_platform_admin_can_access_any_recording():
    """Platform administrators can inspect artifacts across organizations."""
    _check_artifact_access(_profile("platform_admin"), uuid4())


def test_org_admin_can_access_recording_for_their_organization():
    """Organization administrators can inspect their own tenant artifacts."""
    organization_id = uuid4()
    from unittest.mock import Mock

    profile = Mock()
    profile.has_role.side_effect = lambda role, org_id=None: (
        role == "org_admin" and org_id == str(organization_id)
    )

    _check_artifact_access(profile, organization_id)


def test_regular_user_is_denied_recording_access():
    """Recording playback is limited to org and platform administrators."""
    with pytest.raises(HTTPException) as exc_info:
        _check_artifact_access(_profile("regular_user"), uuid4())

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_local_recording_is_streamed_after_admin_authorization(monkeypatch):
    """Local playback never exposes a filesystem path to the browser."""
    call_id = uuid4()
    org_id = uuid4()
    admin = _profile("org_admin")
    admin.has_role.side_effect = lambda role, requested_org=None: (
        role == "org_admin" and requested_org == str(org_id)
    )
    monkeypatch.setattr(
        routes.call_artifact_service,
        "get_recording",
        AsyncMock(
            return_value=(
                {
                    "organization_id": str(org_id),
                    "storage_path": "org/call/recording.wav",
                    "mime_type": "audio/wav",
                },
                None,
            )
        ),
    )
    storage = Mock()
    storage.object_exists = AsyncMock(return_value=True)
    storage.read_object = AsyncMock(return_value=b"RIFF-audio")
    monkeypatch.setattr(routes, "get_recording_storage", lambda: storage)
    monkeypatch.setattr(routes.settings, "recording_storage_backend", "local")

    response = await routes.download_call_recording(call_id, (uuid4(), admin))

    assert response.status_code == 200
    assert response.body == b"RIFF-audio"
    storage.object_exists.assert_not_awaited()
    storage.read_object.assert_awaited_once_with("org/call/recording.wav")


@pytest.mark.asyncio
async def test_r2_recording_streams_through_authenticated_backend(monkeypatch):
    """R2 playback avoids browser CORS by streaming through the backend."""
    call_id = uuid4()
    org_id = uuid4()
    admin = _profile("platform_admin")
    monkeypatch.setattr(
        routes.call_artifact_service,
        "get_recording",
        AsyncMock(
            return_value=(
                {
                    "organization_id": str(org_id),
                    "storage_path": "org/call/recording.wav",
                    "mime_type": "audio/wav",
                },
                None,
            )
        ),
    )
    storage = Mock()
    storage.object_exists = AsyncMock(return_value=True)

    async def stream_object(_key):
        """Yield a small recording body like the storage adapter."""
        yield b"RIFF-"
        yield b"audio"

    storage.stream_object = stream_object
    monkeypatch.setattr(routes, "get_recording_storage", lambda: storage)
    monkeypatch.setattr(routes.settings, "recording_storage_backend", "r2")

    response = await routes.download_call_recording(call_id, (uuid4(), admin))

    assert response.status_code == 200
    assert response.media_type == "audio/wav"
    chunks = [chunk async for chunk in response.body_iterator]
    assert b"".join(chunks) == b"RIFF-audio"


@pytest.mark.asyncio
async def test_missing_local_recording_is_marked_unavailable(monkeypatch):
    """A deleted local object returns a clear gone response and updates metadata."""
    call_id = uuid4()
    org_id = uuid4()
    admin = _profile("platform_admin")
    artifact = {
        "id": str(uuid4()),
        "organization_id": str(org_id),
        "storage_path": "org/call/recording.wav",
        "mime_type": "audio/wav",
    }
    monkeypatch.setattr(
        routes.call_artifact_service,
        "get_recording",
        AsyncMock(return_value=(artifact, None)),
    )
    mark_missing = AsyncMock(return_value=(True, None))
    monkeypatch.setattr(
        routes.call_artifact_service, "mark_recording_missing", mark_missing
    )
    storage = Mock()
    storage.object_exists = AsyncMock()
    storage.read_object = AsyncMock(side_effect=FileNotFoundError)
    monkeypatch.setattr(routes, "get_recording_storage", lambda: storage)
    monkeypatch.setattr(routes.settings, "recording_storage_backend", "local")

    with pytest.raises(HTTPException) as exc_info:
        await routes.download_call_recording(call_id, (uuid4(), admin))

    assert exc_info.value.status_code == 410
    assert exc_info.value.detail == "Recording is no longer available"
    storage.object_exists.assert_not_awaited()
    mark_missing.assert_awaited_once_with(artifact)


@pytest.mark.asyncio
async def test_missing_r2_recording_is_not_redirected(monkeypatch):
    """R2 playback checks object existence before issuing a signed URL."""
    call_id = uuid4()
    org_id = uuid4()
    admin = _profile("platform_admin")
    artifact = {
        "id": str(uuid4()),
        "organization_id": str(org_id),
        "storage_path": "org/call/recording.wav",
        "mime_type": "audio/wav",
    }
    monkeypatch.setattr(
        routes.call_artifact_service,
        "get_recording",
        AsyncMock(return_value=(artifact, None)),
    )
    mark_missing = AsyncMock(return_value=(True, None))
    monkeypatch.setattr(
        routes.call_artifact_service, "mark_recording_missing", mark_missing
    )
    storage = Mock()
    storage.object_exists = AsyncMock(return_value=False)
    storage.get_download_url = AsyncMock()
    monkeypatch.setattr(routes, "get_recording_storage", lambda: storage)
    monkeypatch.setattr(routes.settings, "recording_storage_backend", "r2")

    with pytest.raises(HTTPException) as exc_info:
        await routes.download_call_recording(call_id, (uuid4(), admin))

    assert exc_info.value.status_code == 410
    storage.get_download_url.assert_not_awaited()
    mark_missing.assert_awaited_once_with(artifact)
