"""Capture, encode, and persist call recordings without blocking call teardown."""

from __future__ import annotations

import io
import logging
import wave
from datetime import datetime, timedelta, timezone
from typing import Callable, Optional
from uuid import UUID

from shared.call_recordings.factory import get_recording_storage
from shared.call_recordings.storage import RecordingStorage, build_recording_object_key
from shared.config import settings, supabase_config

logger = logging.getLogger(__name__)


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
    output = io.BytesIO()
    with wave.open(output, "wb") as wav_file:
        wav_file.setnchannels(num_channels)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio)
    return output.getvalue()


class RecordingCoordinator:
    """Own one call's in-memory audio and best-effort artifact persistence.

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
    ):
        """Initialize a coordinator for one organization-scoped call."""
        self.call_log_id = str(call_log_id)
        self.organization_id = str(organization_id)
        self.storage = storage or get_recording_storage()
        self.client = client or supabase_config.client
        self.now = now
        self.retention_days = retention_days or settings.recording_retention_days
        self._audio = bytearray()
        self._sample_rate: Optional[int] = None
        self._num_channels: Optional[int] = None
        self._persisted = False

    async def prepare(self) -> None:
        """Create a pending artifact row before the audio pipeline starts."""
        await self._upsert_artifact(
            status="pending",
            encryption_mode=settings.recording_encryption_mode,
            metadata={"storage_backend": self.storage.bucket},
        )

    def capture_audio(
        self, audio: bytes, *, sample_rate: int, num_channels: int
    ) -> None:
        """Append one mixed PCM buffer emitted by Pipecat's audio processor."""
        if not audio:
            return
        if self._sample_rate is None:
            self._sample_rate = sample_rate
            self._num_channels = num_channels
        elif (self._sample_rate, self._num_channels) != (sample_rate, num_channels):
            raise ValueError("recording audio format changed during one call")
        self._audio.extend(audio)

    async def persist(self) -> bool:
        """Upload the final WAV and mark its artifact completed or failed.

        Returns:
            ``True`` when an audio object and completed metadata row were saved;
            ``False`` when capture was empty or persistence failed.
        """
        if self._persisted:
            return bool(self._audio)
        self._persisted = True
        if not self._audio or not self._sample_rate or not self._num_channels:
            await self._mark_failed("no_audio_captured")
            return False

        try:
            wav = encode_wav(
                bytes(self._audio),
                sample_rate=self._sample_rate,
                num_channels=self._num_channels,
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
            duration_seconds = len(self._audio) // (
                self._sample_rate * self._num_channels * 2
            )
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
                    "sample_rate": self._sample_rate,
                    "num_channels": self._num_channels,
                    "sha256": stored.sha256,
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
