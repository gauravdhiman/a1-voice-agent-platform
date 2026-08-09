"""Tests for voice-worker recording encoding and artifact persistence."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from src.recording import RecordingCoordinator, encode_wav


class _Result:
    """Minimal Supabase response double."""

    def __init__(self, data):
        self.data = data


class _Query:
    """Supabase query double that records artifact writes."""

    def __init__(self, client, operation="select"):
        self.client = client
        self.operation = operation
        self.payload = None

    def upsert(self, payload, **_kwargs):
        self.operation = "upsert"
        self.payload = payload
        return self

    def update(self, payload):
        self.operation = "update"
        self.payload = payload
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def execute(self):
        self.client.writes.append((self.operation, self.payload))
        return _Result([{"id": str(uuid4())}])


class _Client:
    """Supabase client double for recording metadata persistence."""

    def __init__(self):
        self.writes = []

    def table(self, _table):
        return _Query(self)


class _Storage:
    """Recording storage double that returns deterministic object metadata."""

    bucket = "local"

    async def put_object(self, key, data, *, content_type, metadata=None):
        self.key = key
        self.data = data
        self.content_type = content_type
        self.metadata = metadata
        return type(
            "Stored",
            (),
            {
                "bucket": self.bucket,
                "key": key,
                "size_bytes": len(data),
                "sha256": "abc123",
            },
        )()


@pytest.mark.asyncio
async def test_recording_coordinator_uploads_wav_and_completes_artifact():
    """A captured buffer is encoded, uploaded, and marked completed."""
    client = _Client()
    storage = _Storage()
    call_id = uuid4()
    org_id = uuid4()
    coordinator = RecordingCoordinator(
        call_log_id=call_id,
        organization_id=org_id,
        storage=storage,
        client=client,
        now=lambda: datetime(2026, 8, 9, tzinfo=timezone.utc),
    )
    coordinator.capture_audio(b"\x00\x00\x01\x00", sample_rate=8000, num_channels=1)

    result = await coordinator.persist()

    assert result is True
    assert storage.content_type == "audio/wav"
    assert storage.data.startswith(b"RIFF")
    assert storage.data[8:12] == b"WAVE"
    assert any(
        operation == "upsert"
        and payload["status"] == "completed"
        and payload["call_log_id"] == str(call_id)
        for operation, payload in client.writes
    )


@pytest.mark.asyncio
async def test_recording_coordinator_marks_empty_capture_failed():
    """An enabled recording with no audio is visible as a failed artifact."""
    client = _Client()
    coordinator = RecordingCoordinator(
        call_log_id=uuid4(),
        organization_id=uuid4(),
        storage=_Storage(),
        client=client,
    )

    result = await coordinator.persist()

    assert result is False
    assert any(
        operation == "upsert" and payload["status"] == "failed"
        for operation, payload in client.writes
    )


def test_encode_wav_sets_pcm_format():
    """PCM samples are serialized as a playable 16-bit WAV file."""
    wav = encode_wav(b"\x00\x00", sample_rate=16000, num_channels=1)

    assert wav[:4] == b"RIFF"
    assert wav[20:22] == b"\x01\x00"
    assert wav[22:24] == b"\x01\x00"
