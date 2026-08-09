"""Tests for local and R2-compatible call recording storage."""

from pathlib import Path

import pytest

from shared.call_recordings.storage import (
    LocalRecordingStorage,
    R2RecordingStorage,
    RecordingStorageConfigurationError,
    build_recording_object_key,
)


class _Body:
    """Minimal response body for the R2 client test double."""

    def read(self):
        return b"r2-audio"


class _R2Client:
    """Synchronous S3 client double used through ``asyncio.to_thread``."""

    def __init__(self):
        self.calls = []

    def put_object(self, **kwargs):
        self.calls.append(("put", kwargs))

    def get_object(self, **kwargs):
        self.calls.append(("get", kwargs))
        return {"Body": _Body()}

    def head_object(self, **kwargs):
        self.calls.append(("head", kwargs))
        return {}

    def delete_object(self, **kwargs):
        self.calls.append(("delete", kwargs))

    def generate_presigned_url(self, operation, **kwargs):
        self.calls.append(("presign", operation, kwargs))
        return "https://r2.example/signed"


@pytest.mark.asyncio
async def test_local_storage_round_trips_objects_and_returns_metadata(tmp_path: Path):
    """Local development storage writes, reads, and removes recording objects."""
    storage = LocalRecordingStorage(tmp_path)

    stored = await storage.put_object(
        "org-1/call-1/recording.wav",
        b"RIFF-test-audio",
        content_type="audio/wav",
    )

    assert stored.bucket == "local"
    assert stored.key == "org-1/call-1/recording.wav"
    assert stored.size_bytes == len(b"RIFF-test-audio")
    assert await storage.read_object(stored.key) == b"RIFF-test-audio"
    assert await storage.object_exists(stored.key) is True
    assert (tmp_path / stored.key).is_file()

    await storage.delete_object(stored.key)
    assert await storage.object_exists(stored.key) is False
    with pytest.raises(FileNotFoundError):
        await storage.read_object(stored.key)


def test_recording_object_key_is_organization_scoped():
    """Object keys contain a stable tenant boundary and recording filename."""
    key = build_recording_object_key("org-1", "call-1")

    assert key.startswith("org-1/calls/")
    assert key.endswith("/call-1/recording.wav")


@pytest.mark.asyncio
async def test_local_storage_rejects_path_escape(tmp_path: Path):
    """A caller cannot use an object key to write outside the recording root."""
    storage = LocalRecordingStorage(tmp_path)

    with pytest.raises(ValueError, match="safe relative"):
        await storage.put_object("../outside.wav", b"audio", content_type="audio/wav")


def test_customer_managed_mode_is_not_silently_downgraded():
    """Unsupported customer-managed encryption fails explicitly."""
    from shared.call_recordings.storage import validate_encryption_mode

    with pytest.raises(RecordingStorageConfigurationError, match="customer-managed"):
        validate_encryption_mode("customer_managed")


@pytest.mark.asyncio
async def test_r2_storage_uses_private_bucket_and_short_lived_get_url():
    """The R2 adapter uses bucket-scoped operations and presigned GETs."""
    client = _R2Client()
    storage = R2RecordingStorage(
        endpoint="https://account.r2.cloudflarestorage.com",
        bucket="staging-recordings",
        access_key_id="access",
        secret_access_key="secret",
        client=client,
    )

    stored = await storage.put_object(
        "org/call/recording.wav",
        b"r2-audio",
        content_type="audio/wav",
        metadata={"organization_id": "org"},
    )
    assert stored.bucket == "staging-recordings"
    assert await storage.read_object(stored.key) == b"r2-audio"
    assert await storage.object_exists(stored.key) is True
    assert await storage.get_download_url(stored.key, expires_in=300) == (
        "https://r2.example/signed"
    )
    await storage.delete_object(stored.key)

    assert client.calls[0][1]["Bucket"] == "staging-recordings"
    assert client.calls[0][1]["ContentType"] == "audio/wav"
    presign_call = next(call for call in client.calls if call[0] == "presign")
    assert presign_call[2]["ExpiresIn"] == 300
