"""Configuration-driven factory for private call-recording storage."""

from __future__ import annotations

from pathlib import Path

from shared.config import settings
from shared.config.settings import PROJECT_ROOT

from .storage import (
    LocalRecordingStorage,
    R2RecordingStorage,
    RecordingStorage,
    RecordingStorageConfigurationError,
    validate_encryption_mode,
)


def get_recording_storage() -> RecordingStorage:
    """Build the configured private recording store.

    Provider-managed encryption is the current production strategy. The
    validation call deliberately rejects customer-managed mode until a key
    provider, rotation policy, and recovery workflow are implemented together.

    Returns:
        Configured local or R2 storage adapter.

    Raises:
        RecordingStorageConfigurationError: If encryption or R2 credentials
            are incomplete.
    """
    validate_encryption_mode(settings.recording_encryption_mode)
    if settings.recording_storage_backend == "local":
        root = Path(settings.recording_storage_local_root)
        if not root.is_absolute():
            root = PROJECT_ROOT / root
        return LocalRecordingStorage(root)

    if settings.recording_storage_backend == "r2":
        return R2RecordingStorage(
            endpoint=settings.recording_r2_endpoint or "",
            bucket=settings.recording_r2_bucket or "",
            access_key_id=settings.recording_r2_access_key_id or "",
            secret_access_key=settings.recording_r2_secret_access_key or "",
        )

    raise RecordingStorageConfigurationError(
        f"unsupported recording storage backend: {settings.recording_storage_backend}"
    )
