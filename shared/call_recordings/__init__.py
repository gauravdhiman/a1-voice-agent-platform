"""Shared call-recording storage and serialization contracts."""

from .factory import get_recording_storage
from .storage import (
    LocalRecordingStorage,
    R2RecordingStorage,
    RecordingStorage,
    RecordingStorageConfigurationError,
    StoredObject,
    build_recording_object_key,
    validate_encryption_mode,
)

__all__ = [
    "LocalRecordingStorage",
    "R2RecordingStorage",
    "RecordingStorage",
    "RecordingStorageConfigurationError",
    "StoredObject",
    "build_recording_object_key",
    "validate_encryption_mode",
    "get_recording_storage",
]
