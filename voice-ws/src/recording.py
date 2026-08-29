"""Capture, encode, and persist call recordings without blocking call teardown."""

from __future__ import annotations

import asyncio
import io
import logging
import time
import wave
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Callable, Literal, Optional
from uuid import UUID

import numpy as np
import soxr
from pipecat.frames.frames import Frame, InputAudioRawFrame, OutputAudioRawFrame
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

from shared.call_recordings.factory import get_recording_storage
from shared.call_recordings.storage import RecordingStorage, build_recording_object_key
from shared.config import settings, supabase_config

logger = logging.getLogger(__name__)

RecordingTrack = Literal["caller", "agent"]


def encode_wav(audio: bytes, *, sample_rate: int, num_channels: int) -> bytes:
    """Encode signed 16-bit PCM bytes as a standard WAV file.

    Args:
        audio: Interleaved signed 16-bit PCM samples.
        sample_rate: Samples per second.
        num_channels: Number of interleaved audio channels.

    Returns:
        Complete RIFF/WAVE bytes suitable for object storage and browser playback.
    """
    if sample_rate <= 0 or num_channels <= 0:
        raise ValueError("sample_rate and num_channels must be positive")
    if len(audio) % (2 * num_channels):
        raise ValueError("audio length must contain complete PCM frames")
    output = io.BytesIO()
    with wave.open(output, "wb") as wav_file:
        wav_file.setnchannels(num_channels)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio)
    return output.getvalue()


@dataclass
class _TrackBuffer:
    """Raw mono PCM captured for one side of a call."""

    audio: bytearray = field(default_factory=bytearray)
    sample_rate: Optional[int] = None
    num_channels: Optional[int] = None
    first_capture_at: Optional[float] = None
    last_audio_end_at: Optional[float] = None


_MIN_CAPTURE_GAP_SECONDS = 0.2


def _resample_mono_pcm(audio: bytes, *, source_rate: int, target_rate: int) -> bytes:
    """Resample a complete mono PCM track without streaming state loss."""
    if source_rate == target_rate or not audio:
        return audio
    samples = np.frombuffer(audio, dtype="<i2")
    resampled = soxr.resample(
        samples,
        source_rate,
        target_rate,
        quality="HQ",
    )
    return np.clip(np.rint(resampled), -32768, 32767).astype("<i2").tobytes()


def _interleave_tracks(
    caller: bytes,
    agent: bytes,
    *,
    caller_offset_samples: int = 0,
    agent_offset_samples: int = 0,
) -> bytes:
    """Interleave mono caller/agent tracks, padding the shorter track.

    The resulting stereo layout is caller on the left and agent on the right.
    Offsets are captured at the transport boundaries. They preserve the
    genuine delay before a track starts without allowing downstream model or
    output-transport backpressure to create artificial silence.
    """
    caller_samples = np.frombuffer(caller, dtype="<i2")
    agent_samples = np.frombuffer(agent, dtype="<i2")
    frame_count = max(
        caller_offset_samples + len(caller_samples),
        agent_offset_samples + len(agent_samples),
    )
    if frame_count == 0:
        return b""

    stereo = np.zeros((frame_count, 2), dtype=np.int16)
    stereo[caller_offset_samples : caller_offset_samples + len(caller_samples), 0] = (
        caller_samples
    )
    stereo[agent_offset_samples : agent_offset_samples + len(agent_samples), 1] = (
        agent_samples
    )
    return stereo.tobytes()


class RecordingAudioTap(FrameProcessor):
    """Pass through frames while capturing one transport-adjacent audio track.

    A caller tap belongs immediately after ``transport.input()``. An agent tap
    belongs immediately before ``transport.output()``. Capturing at those
    boundaries prevents model processing, output playback pacing, and
    downstream backpressure from changing the caller's audio bytes or duration.
    """

    def __init__(
        self,
        coordinator: "RecordingCoordinator",
        *,
        track: RecordingTrack,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        """Initialize a pass-through tap for ``caller`` or ``agent`` audio."""
        if track not in ("caller", "agent"):
            raise ValueError(f"unsupported recording track: {track}")
        super().__init__(name=f"recording-{track}-tap")
        self._coordinator = coordinator
        self._track = track
        # Keep capture timing separate from Pipecat's processor lifecycle
        # clock. Pipecat owns the framework clock and its setup representation
        # can change across runtime releases.
        self._capture_clock = clock
        self._capture_enabled = True

    async def process_frame(self, frame: Frame, direction: FrameDirection) -> None:
        """Capture matching downstream audio and always preserve frame flow."""
        expected_type = (
            InputAudioRawFrame if self._track == "caller" else OutputAudioRawFrame
        )
        captured_at = (
            self._capture_clock()
            if self._capture_enabled
            and direction == FrameDirection.DOWNSTREAM
            and isinstance(frame, expected_type)
            else None
        )
        await super().process_frame(frame, direction)
        if captured_at is not None:
            try:
                self._coordinator.capture_track_audio(
                    self._track,
                    frame.audio,
                    sample_rate=frame.sample_rate,
                    num_channels=frame.num_channels,
                    captured_at=captured_at,
                )
            except Exception as exc:  # noqa: BLE001 - recording is best effort
                self._capture_enabled = False
                self._coordinator.note_capture_error(
                    f"{self._track}:{type(exc).__name__}"
                )
                logger.exception(
                    "Recording tap disabled after invalid %s audio frame",
                    self._track,
                )
        await self.push_frame(frame, direction)


class RecordingCoordinator:
    """Own one call's audio and best-effort artifact persistence.

    Caller and agent frames are captured independently as raw mono PCM. The
    final stereo WAV is rendered once at the lowest native track sample rate,
    so a 16 kHz caller is never upsampled to a 24 kHz agent output. Rendering
    is separate from the live pipeline and does not infer silence from
    processing latency.

    The coordinator intentionally persists only after Pipecat finishes. If
    storage or metadata persistence fails, the exception is logged and the
    caller can still finalize duration and credit accounting.
    """

    def __init__(
        self,
        *,
        call_log_id: UUID | str,
        organization_id: UUID | str,
        storage: Optional[RecordingStorage] = None,
        client=None,
        now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
        retention_days: Optional[int] = None,
        session_started_at: Optional[float] = None,
    ):
        """Initialize a coordinator for one organization-scoped call."""
        self.call_log_id = str(call_log_id)
        self.organization_id = str(organization_id)
        self.storage = storage or get_recording_storage()
        self.client = client or supabase_config.client
        self.now = now
        self.retention_days = retention_days or settings.recording_retention_days
        self._session_started_at = (
            time.monotonic() if session_started_at is None else session_started_at
        )
        self._tracks: dict[RecordingTrack, _TrackBuffer] = {
            "caller": _TrackBuffer(),
            "agent": _TrackBuffer(),
        }
        # Kept for callers compiled against the original mixed-buffer API.
        # New runtime code uses capture_track_audio through RecordingAudioTap.
        self._legacy_audio = bytearray()
        self._legacy_sample_rate: Optional[int] = None
        self._legacy_num_channels: Optional[int] = None
        self._capture_error: Optional[str] = None
        self._persisted = False

    async def prepare(self) -> None:
        """Create a pending artifact row before the audio pipeline starts."""
        await self._upsert_artifact(
            status="pending",
            encryption_mode=settings.recording_encryption_mode,
            metadata={"storage_backend": self.storage.bucket},
        )

    def capture_track_audio(
        self,
        track: RecordingTrack,
        audio: bytes,
        *,
        sample_rate: int,
        num_channels: int,
        captured_at: Optional[float] = None,
    ) -> None:
        """Append raw mono PCM audio for one side of the call.

        Raises:
            ValueError: If the frame is not valid signed 16-bit mono PCM or its
                format changes during the call.
        """
        if track not in self._tracks:
            raise ValueError(f"unsupported recording track: {track}")
        if not audio:
            return
        if sample_rate <= 0 or num_channels != 1:
            raise ValueError("recording tracks must be positive-rate mono PCM")
        if len(audio) % 2:
            raise ValueError("recording audio must contain complete 16-bit samples")

        buffer = self._tracks[track]
        if buffer.sample_rate is None:
            buffer.sample_rate = sample_rate
            buffer.num_channels = num_channels
        elif (buffer.sample_rate, buffer.num_channels) != (
            sample_rate,
            num_channels,
        ):
            raise ValueError(f"{track} recording audio format changed during call")

        captured_at = time.monotonic() if captured_at is None else captured_at
        frame_duration = len(audio) / (sample_rate * 2)
        if buffer.first_capture_at is None:
            buffer.first_capture_at = captured_at
            buffer.last_audio_end_at = captured_at
        elif buffer.last_audio_end_at is not None:
            gap = captured_at - buffer.last_audio_end_at
            if gap > _MIN_CAPTURE_GAP_SECONDS:
                silence_samples = int(round(gap * sample_rate))
                buffer.audio.extend(b"\x00\x00" * silence_samples)
                buffer.last_audio_end_at = captured_at
            else:
                # If a provider emits several output chunks in a burst, keep
                # their audio contiguous instead of compressing its duration.
                buffer.last_audio_end_at = max(captured_at, buffer.last_audio_end_at)
        buffer.audio.extend(audio)
        buffer.last_audio_end_at = (
            buffer.last_audio_end_at or captured_at
        ) + frame_duration

    def capture_audio(
        self, audio: bytes, *, sample_rate: int, num_channels: int
    ) -> None:
        """Append an already mixed PCM buffer for legacy callers.

        Runtime recording uses :meth:`capture_track_audio`; this compatibility
        method remains so an older caller cannot silently lose its recording
        while deployments are rolled forward.
        """
        if not audio:
            return
        if sample_rate <= 0 or num_channels <= 0:
            raise ValueError("sample_rate and num_channels must be positive")
        if len(audio) % (2 * num_channels):
            raise ValueError("audio length must contain complete PCM frames")
        if self._legacy_sample_rate is None:
            self._legacy_sample_rate = sample_rate
            self._legacy_num_channels = num_channels
        elif (self._legacy_sample_rate, self._legacy_num_channels) != (
            sample_rate,
            num_channels,
        ):
            raise ValueError("recording audio format changed during one call")
        self._legacy_audio.extend(audio)

    def note_capture_error(self, reason: str) -> None:
        """Record a redacted capture warning without affecting call execution."""
        if self._capture_error is None:
            self._capture_error = reason

    def has_captured_audio(self) -> bool:
        """Return whether any valid audio has been captured."""
        return bool(
            self._legacy_audio or any(track.audio for track in self._tracks.values())
        )

    def _build_recording(self) -> tuple[bytes, int, int, dict[str, object]]:
        """Render WAV bytes and metadata from the captured tracks."""
        if self._legacy_audio:
            if not self._legacy_sample_rate or not self._legacy_num_channels:
                raise ValueError("legacy recording format is missing")
            pcm = bytes(self._legacy_audio)
            return (
                encode_wav(
                    pcm,
                    sample_rate=self._legacy_sample_rate,
                    num_channels=self._legacy_num_channels,
                ),
                self._legacy_sample_rate,
                self._legacy_num_channels,
                {"capture_mode": "legacy_mixed"},
            )

        active_tracks = {
            name: track for name, track in self._tracks.items() if track.audio
        }
        if not active_tracks:
            raise ValueError("no_audio_captured")

        source_rates = {
            name: track.sample_rate
            for name, track in active_tracks.items()
            if track.sample_rate is not None
        }
        if not source_rates:
            raise ValueError("recording source sample rate is missing")
        target_rate = min(source_rates.values())

        rendered: dict[RecordingTrack, bytes] = {"caller": b"", "agent": b""}
        offsets: dict[RecordingTrack, int] = {"caller": 0, "agent": 0}
        for name, track in active_tracks.items():
            if track.sample_rate is None or track.num_channels != 1:
                raise ValueError(f"{name} recording format is missing or invalid")
            rendered[name] = _resample_mono_pcm(
                bytes(track.audio),
                source_rate=track.sample_rate,
                target_rate=target_rate,
            )
            if track.first_capture_at is not None:
                offsets[name] = max(
                    0,
                    int(
                        round(
                            (track.first_capture_at - self._session_started_at)
                            * target_rate
                        )
                    ),
                )

        pcm = _interleave_tracks(
            rendered["caller"],
            rendered["agent"],
            caller_offset_samples=offsets["caller"],
            agent_offset_samples=offsets["agent"],
        )
        if not pcm:
            raise ValueError("resampling produced no audio")
        metadata: dict[str, object] = {
            "capture_mode": "transport_taps",
            "source_sample_rates": source_rates,
            "output_sample_rate": target_rate,
            "tracks_captured": sorted(active_tracks),
        }
        if self._capture_error:
            metadata["capture_warning"] = self._capture_error
        return (
            encode_wav(pcm, sample_rate=target_rate, num_channels=2),
            target_rate,
            2,
            metadata,
        )

    async def persist(self) -> bool:
        """Upload the final WAV and mark its artifact completed or failed.

        Returns:
            ``True`` when an audio object and completed metadata row were saved;
            ``False`` when capture was empty or persistence failed.
        """
        if self._persisted:
            return self.has_captured_audio()
        self._persisted = True
        if not self.has_captured_audio():
            await self._mark_failed("no_audio_captured")
            return False

        try:
            wav, sample_rate, num_channels, recording_metadata = (
                await asyncio.to_thread(self._build_recording)
            )
            recorded_at = self.now()
            key = build_recording_object_key(
                self.organization_id,
                self.call_log_id,
                recorded_at,
            )
            stored = await self.storage.put_object(
                key,
                wav,
                content_type="audio/wav",
                metadata={
                    "organization_id": self.organization_id,
                    "call_log_id": self.call_log_id,
                },
            )
            with wave.open(io.BytesIO(wav), "rb") as recording:
                duration_seconds = recording.getnframes() // recording.getframerate()
            retention_expires_at = recorded_at + timedelta(days=self.retention_days)
            await self._upsert_artifact(
                status="completed",
                encryption_mode=settings.recording_encryption_mode,
                storage_bucket=stored.bucket,
                storage_path=stored.key,
                mime_type="audio/wav",
                size_bytes=stored.size_bytes,
                duration_seconds=duration_seconds,
                retention_expires_at=retention_expires_at.isoformat(),
                metadata={
                    "storage_backend": stored.bucket,
                    "encryption_mode": settings.recording_encryption_mode,
                    "sample_rate": sample_rate,
                    "num_channels": num_channels,
                    "sha256": stored.sha256,
                    **recording_metadata,
                },
            )
            return True
        except Exception as exc:  # noqa: BLE001 - recording is best effort
            logger.exception(
                "Failed to persist recording for call %s", self.call_log_id
            )
            await self._mark_failed(type(exc).__name__)
            return False

    async def _mark_failed(self, reason: str) -> None:
        """Expose a non-blocking failed state for support and retry tooling."""
        try:
            await self._upsert_artifact(
                status="failed",
                encryption_mode=settings.recording_encryption_mode,
                metadata={
                    "storage_backend": self.storage.bucket,
                    "failure_reason": reason,
                },
            )
        except Exception:  # noqa: BLE001 - preserve call teardown
            logger.exception("Failed to mark recording artifact as failed")

    async def _upsert_artifact(self, **fields) -> None:
        """Upsert one organization-scoped recording artifact row."""
        payload = {
            "call_log_id": self.call_log_id,
            "organization_id": self.organization_id,
            "artifact_type": "recording",
            "status": fields.pop("status"),
            "updated_at": self.now().isoformat(),
            **fields,
        }
        result = (
            self.client.table("call_artifacts")
            .upsert(payload, on_conflict="call_log_id,artifact_type")
            .execute()
        )
        if hasattr(result, "data") and result.data is None:
            raise RuntimeError("call artifact upsert returned no response")
