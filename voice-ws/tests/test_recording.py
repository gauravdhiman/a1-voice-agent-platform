"""Tests for voice-worker recording capture, encoding, and persistence."""

import asyncio
import io
import struct
import wave
from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from pipecat.frames.frames import InputAudioRawFrame, OutputAudioRawFrame
from pipecat.processors.frame_processor import FrameDirection, FrameProcessorSetup
from src.recording import RecordingAudioTap, RecordingCoordinator, encode_wav


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
async def test_transport_tracks_preserve_boundary_timing_without_processing_gaps():
    """Boundary capture preserves timing without adding downstream delay."""
    capture_times = iter((100.0, 100.02, 100.04))
    client = _Client()
    storage = _Storage()
    coordinator = RecordingCoordinator(
        call_log_id=uuid4(),
        organization_id=uuid4(),
        storage=storage,
        client=client,
        session_started_at=100.0,
    )
    caller_tap = RecordingAudioTap(
        coordinator, track="caller", clock=lambda: next(capture_times)
    )
    agent_tap = RecordingAudioTap(
        coordinator, track="agent", clock=lambda: next(capture_times)
    )
    caller_tap.push_frame = AsyncMock()
    agent_tap.push_frame = AsyncMock()

    await caller_tap.process_frame(
        InputAudioRawFrame(
            audio=b"\x01\x00" * 320,
            sample_rate=16000,
            num_channels=1,
        ),
        FrameDirection.DOWNSTREAM,
    )
    await asyncio.sleep(0.25)
    await caller_tap.process_frame(
        InputAudioRawFrame(
            audio=b"\x01\x00" * 320,
            sample_rate=16000,
            num_channels=1,
        ),
        FrameDirection.DOWNSTREAM,
    )
    await agent_tap.process_frame(
        OutputAudioRawFrame(
            audio=b"\x02\x00" * 960,
            sample_rate=24000,
            num_channels=1,
        ),
        FrameDirection.DOWNSTREAM,
    )

    result = await coordinator.persist()

    assert result is True
    with wave.open(io.BytesIO(storage.data), "rb") as recording:
        assert recording.getframerate() == 16000
        assert recording.getnchannels() == 2
        assert recording.getnframes() == 1280
        samples = struct.unpack(
            "<" + "h" * (recording.getnframes() * 2), recording.readframes(1280)
        )
    assert samples[::2][:640] == (1,) * 640
    assert samples[::2][640:] == (0,) * 640
    assert samples[1::2][:640] == (0,) * 640
    assert any(samples[1::2][640:])
    completed = next(
        payload
        for operation, payload in client.writes
        if payload["status"] == "completed"
    )
    assert completed["metadata"]["capture_mode"] == "transport_taps"
    assert completed["metadata"]["source_sample_rates"] == {
        "caller": 16000,
        "agent": 24000,
    }


@pytest.mark.asyncio
async def test_recording_tap_clock_survives_pipecat_processor_setup():
    """Pipecat setup must not replace the tap's capture clock callable."""
    client = _Client()
    coordinator = RecordingCoordinator(
        call_log_id=uuid4(),
        organization_id=uuid4(),
        storage=_Storage(),
    )
    tap = RecordingAudioTap(
        coordinator,
        track="caller",
        clock=lambda: 100.0,
    )
    # Direct mode avoids starting an internal processor task in this lifecycle
    # test; the production pipeline still exercises normal queued processing.
    tap._enable_direct_mode = True
    framework_clock = object()
    await tap.setup(
        FrameProcessorSetup(
            clock=framework_clock,
            task_manager=object(),
            pipeline_worker=object(),
        )
    )
    tap.push_frame = AsyncMock()

    frame = InputAudioRawFrame(
        audio=b"\x01\x00" * 160,
        sample_rate=16000,
        num_channels=1,
    )
    await tap.process_frame(frame, FrameDirection.DOWNSTREAM)

    assert tap._clock is framework_clock
    assert coordinator._tracks["caller"].audio == bytearray(frame.audio)
    tap.push_frame.assert_awaited_once_with(frame, FrameDirection.DOWNSTREAM)


@pytest.mark.asyncio
async def test_recording_tap_preserves_frames_when_capture_fails():
    """A malformed frame cannot interrupt the live pipeline."""
    client = _Client()
    coordinator = RecordingCoordinator(
        call_log_id=uuid4(),
        organization_id=uuid4(),
        storage=_Storage(),
        client=client,
    )

    def reject_capture(*_args, **_kwargs):
        raise ValueError("bad audio")

    coordinator.capture_track_audio = reject_capture
    tap = RecordingAudioTap(coordinator, track="caller")
    tap.push_frame = AsyncMock()
    frame = InputAudioRawFrame(audio=b"\x01\x00", sample_rate=16000, num_channels=1)

    await tap.process_frame(frame, FrameDirection.DOWNSTREAM)

    tap.push_frame.assert_awaited_once_with(frame, FrameDirection.DOWNSTREAM)
    assert coordinator._capture_error == "caller:ValueError"


@pytest.mark.asyncio
async def test_caller_only_capture_keeps_a_stereo_agent_silence_channel():
    """A one-sided call remains listenable without dropping the caller track."""
    client = _Client()
    storage = _Storage()
    coordinator = RecordingCoordinator(
        call_log_id=uuid4(),
        organization_id=uuid4(),
        storage=storage,
        client=client,
    )
    coordinator.capture_track_audio(
        "caller",
        b"\x05\x00" * 16000,
        sample_rate=16000,
        num_channels=1,
    )

    result = await coordinator.persist()

    assert result is True
    with wave.open(io.BytesIO(storage.data), "rb") as recording:
        assert recording.getframerate() == 16000
        assert recording.getnchannels() == 2
        assert recording.getnframes() == 16000
        samples = recording.readframes(16000)
    left = samples[::4]
    right = samples[2::4]
    assert left and any(left)
    assert right and not any(right)
    completed = next(
        payload
        for operation, payload in client.writes
        if payload["status"] == "completed"
    )
    assert completed["duration_seconds"] == 1


@pytest.mark.asyncio
async def test_telephony_rate_tracks_render_at_the_lowest_native_rate():
    """An 8 kHz caller track remains valid when agent audio is higher-rate."""
    client = _Client()
    storage = _Storage()
    coordinator = RecordingCoordinator(
        call_log_id=uuid4(),
        organization_id=uuid4(),
        storage=storage,
        client=client,
        session_started_at=100.0,
    )
    coordinator.capture_track_audio(
        "caller",
        b"\x05\x00" * 160,
        sample_rate=8000,
        num_channels=1,
        captured_at=100.0,
    )
    coordinator.capture_track_audio(
        "agent",
        b"\x06\x00" * 480,
        sample_rate=24000,
        num_channels=1,
        captured_at=100.0,
    )

    result = await coordinator.persist()

    assert result is True
    with wave.open(io.BytesIO(storage.data), "rb") as recording:
        assert recording.getframerate() == 8000
        assert recording.getnchannels() == 2
        assert recording.getnframes() == 160


def test_recording_track_rejects_non_mono_or_partial_pcm():
    """Malformed provider audio is rejected before it can corrupt a WAV."""
    coordinator = RecordingCoordinator(
        call_log_id=uuid4(),
        organization_id=uuid4(),
        storage=_Storage(),
        client=_Client(),
    )

    with pytest.raises(ValueError, match="mono PCM"):
        coordinator.capture_track_audio(
            "caller", b"\x00\x00", sample_rate=16000, num_channels=2
        )
    with pytest.raises(ValueError, match="16-bit samples"):
        coordinator.capture_track_audio(
            "caller", b"\x00", sample_rate=16000, num_channels=1
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
