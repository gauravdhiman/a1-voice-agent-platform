"""Private object storage adapters for call recordings.

The application stores only object metadata in Postgres. This module keeps the
voice worker and backend independent of the storage provider, with a local
filesystem adapter for development and an S3-compatible adapter for Cloudflare
R2 in staging and production.
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, AsyncIterator, Mapping, Optional, Protocol


class RecordingStorageConfigurationError(ValueError):
    """Raised when recording storage or encryption configuration is unsafe."""


class RecordingStorage(Protocol):
    """Async contract implemented by local and R2 recording stores."""

    bucket: str

    async def put_object(
        self,
        key: str,
        data: bytes,
        *,
        content_type: str,
        metadata: Optional[Mapping[str, str]] = None,
    ) -> "StoredObject":
        """Store an object and return integrity metadata."""

    async def read_object(self, key: str) -> bytes:
        """Read a private object by its internal key."""

    def stream_object(self, key: str) -> AsyncIterator[bytes]:
        """Yield a private object in bounded chunks for HTTP playback."""

    async def object_exists(self, key: str) -> bool:
        """Check whether a private object is currently available."""

    async def delete_object(self, key: str) -> None:
        """Delete a private object by its internal key."""

    async def get_download_url(self, key: str, *, expires_in: int) -> Optional[str]:
        """Return a short-lived URL when the provider supports direct playback."""


@dataclass(frozen=True)
class StoredObject:
    """Metadata returned after an object has been written."""

    bucket: str
    key: str
    size_bytes: int
    sha256: str


def validate_encryption_mode(mode: str) -> str:
    """Validate the configured recording encryption strategy.

    Cloudflare R2 already encrypts objects at rest with provider-managed keys.
    Customer-provided keys require a separate key lifecycle and are deliberately
    rejected until that strategy is implemented end to end. Rejecting the mode
    prevents a configuration typo from silently storing customer-mode data with
    provider-managed encryption.

    Args:
        mode: Encryption strategy name from application configuration.

    Returns:
        The validated ``provider_managed`` strategy name.

    Raises:
        RecordingStorageConfigurationError: If the strategy is unsupported.
    """
    if mode == "provider_managed":
        return mode
    if mode == "customer_managed":
        raise RecordingStorageConfigurationError(
            "customer-managed recording encryption is reserved for a future "
            "key-management integration; use provider_managed for now"
        )
    raise RecordingStorageConfigurationError(
        f"unsupported recording encryption mode: {mode}"
    )


def build_recording_object_key(
    organization_id: str,
    call_log_id: str,
    recorded_at: Optional[datetime] = None,
) -> str:
    """Build a tenant-scoped, date-partitioned recording object key.

    Args:
        organization_id: Owning organization identifier.
        call_log_id: Call-log identifier associated with the recording.
        recorded_at: Optional UTC timestamp used for partitioning. Defaults to
            the current UTC time.

    Returns:
        A private object key such as
        ``org-id/calls/2026/08/09/call-id/recording.wav``.
    """
    timestamp = recorded_at or datetime.now(timezone.utc)
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    timestamp = timestamp.astimezone(timezone.utc)
    return (
        f"{organization_id}/calls/{timestamp:%Y/%m/%d}/" f"{call_log_id}/recording.wav"
    )


def _safe_relative_path(root: Path, key: str) -> Path:
    """Resolve a storage key beneath ``root`` without permitting traversal."""
    if not key or "\x00" in key:
        raise ValueError("recording object key must be a safe relative path")
    relative = PurePosixPath(key)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("recording object key must be a safe relative path")
    destination = (root / Path(*relative.parts)).resolve()
    try:
        destination.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError("recording object key must be a safe relative path") from exc
    return destination


class LocalRecordingStorage:
    """Store private recordings under an ignored local-development directory."""

    bucket = "local"

    def __init__(self, root: Path | str):
        """Initialize local storage at ``root`` and create it if necessary."""
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    async def put_object(
        self,
        key: str,
        data: bytes,
        *,
        content_type: str,
        metadata: Optional[Mapping[str, str]] = None,
    ) -> StoredObject:
        """Write bytes atomically beneath the local recording root."""
        del content_type, metadata
        destination = _safe_relative_path(self.root, key)
        return await asyncio.to_thread(self._put_object, destination, key, data)

    def _put_object(self, destination: Path, key: str, data: bytes) -> StoredObject:
        """Synchronous atomic write used by ``put_object``."""
        destination.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary_name = tempfile.mkstemp(
            prefix=f".{destination.name}.", dir=destination.parent
        )
        try:
            with os.fdopen(fd, "wb") as temporary_file:
                temporary_file.write(data)
                temporary_file.flush()
                os.fsync(temporary_file.fileno())
            os.replace(temporary_name, destination)
        finally:
            if os.path.exists(temporary_name):
                os.unlink(temporary_name)
        return StoredObject(
            bucket=self.bucket,
            key=key,
            size_bytes=len(data),
            sha256=hashlib.sha256(data).hexdigest(),
        )

    async def read_object(self, key: str) -> bytes:
        """Read a local recording object, raising ``FileNotFoundError`` if absent."""
        destination = _safe_relative_path(self.root, key)
        return await asyncio.to_thread(destination.read_bytes)

    async def stream_object(self, key: str) -> AsyncIterator[bytes]:
        """Yield a local recording as one chunk through the authenticated API."""
        yield await self.read_object(key)

    async def object_exists(self, key: str) -> bool:
        """Check local object availability without reading the audio bytes."""
        destination = _safe_relative_path(self.root, key)
        return await asyncio.to_thread(destination.is_file)

    async def delete_object(self, key: str) -> None:
        """Delete a local recording object if it exists."""
        destination = _safe_relative_path(self.root, key)

        def remove() -> None:
            """Remove the file without making cleanup retries fail."""
            try:
                destination.unlink()
            except FileNotFoundError:
                return

        await asyncio.to_thread(remove)

    async def get_download_url(self, key: str, *, expires_in: int) -> Optional[str]:
        """Local files are served through the authenticated backend endpoint."""
        del key, expires_in
        return None


class R2RecordingStorage:
    """Store recordings in a private Cloudflare R2 bucket via its S3 API."""

    def __init__(
        self,
        *,
        endpoint: str,
        bucket: str,
        access_key_id: str,
        secret_access_key: str,
        client: Any = None,
    ):
        """Initialize the R2 adapter with bucket-scoped credentials.

        The optional client argument is intentionally injectable for unit tests.
        Production callers omit it and use the lazily imported boto3 client.
        """
        missing = [
            name
            for name, value in {
                "endpoint": endpoint,
                "bucket": bucket,
                "access_key_id": access_key_id,
                "secret_access_key": secret_access_key,
            }.items()
            if not value
        ]
        if missing:
            raise RecordingStorageConfigurationError(
                f"R2 recording storage is missing: {', '.join(missing)}"
            )
        self.endpoint = endpoint.rstrip("/")
        self.bucket = bucket
        self._client = client or self._create_client(access_key_id, secret_access_key)

    def _create_client(self, access_key_id: str, secret_access_key: str) -> Any:
        """Create a boto3 S3 client only when R2 storage is selected."""
        try:
            import boto3
        except ImportError as exc:
            raise RecordingStorageConfigurationError(
                "R2 recording storage requires the boto3 dependency"
            ) from exc
        return boto3.client(
            "s3",
            endpoint_url=self.endpoint,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name="auto",
        )

    async def put_object(
        self,
        key: str,
        data: bytes,
        *,
        content_type: str,
        metadata: Optional[Mapping[str, str]] = None,
    ) -> StoredObject:
        """Upload bytes to R2 with a private content type and metadata."""
        kwargs: dict[str, Any] = {
            "Bucket": self.bucket,
            "Key": key,
            "Body": data,
            "ContentType": content_type,
        }
        if metadata:
            kwargs["Metadata"] = dict(metadata)
        await asyncio.to_thread(self._client.put_object, **kwargs)
        return StoredObject(
            bucket=self.bucket,
            key=key,
            size_bytes=len(data),
            sha256=hashlib.sha256(data).hexdigest(),
        )

    async def read_object(self, key: str) -> bytes:
        """Read an object from R2 using service credentials."""
        response = await asyncio.to_thread(
            self._client.get_object, Bucket=self.bucket, Key=key
        )
        return await asyncio.to_thread(response["Body"].read)

    async def stream_object(self, key: str) -> AsyncIterator[bytes]:
        """Yield an R2 object in bounded chunks without buffering full audio."""
        response = await asyncio.to_thread(
            self._client.get_object, Bucket=self.bucket, Key=key
        )
        body = response["Body"]
        try:
            while True:
                chunk = await asyncio.to_thread(body.read, 1024 * 1024)
                if not chunk:
                    break
                yield chunk
        finally:
            close = getattr(body, "close", None)
            if close:
                await asyncio.to_thread(close)

    async def object_exists(self, key: str) -> bool:
        """Check R2 object availability with a metadata-only HEAD request."""
        try:
            await asyncio.to_thread(
                self._client.head_object, Bucket=self.bucket, Key=key
            )
            return True
        except Exception as exc:  # noqa: BLE001 - boto3 exception shape varies
            response = getattr(exc, "response", None) or {}
            error = response.get("Error", {})
            code = str(error.get("Code", ""))
            if code in {"404", "NoSuchKey", "NotFound"}:
                return False
            raise

    async def delete_object(self, key: str) -> None:
        """Delete an object from R2."""
        await asyncio.to_thread(self._client.delete_object, Bucket=self.bucket, Key=key)

    async def get_download_url(self, key: str, *, expires_in: int) -> Optional[str]:
        """Create a short-lived GET URL; the bucket remains private."""
        return await asyncio.to_thread(
            self._client.generate_presigned_url,
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=expires_in,
        )
