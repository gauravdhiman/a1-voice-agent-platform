"""Twilio Media Streams helpers for the voice-ws worker.

Builds a :class:`TwilioFrameSerializer` from Pipecat's telephony handshake
payload. Auto hang-up is enabled only when Twilio REST credentials are present.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Mapping, Optional

from pipecat.serializers.twilio import TwilioFrameSerializer

logger = logging.getLogger(__name__)


def build_twilio_serializer(
    call_data: Mapping[str, Any] | Any,
    *,
    account_sid: Optional[str] = None,
    auth_token: Optional[str] = None,
) -> TwilioFrameSerializer:
    """Create a Twilio Media Streams frame serializer from parsed call data.

    Args:
        call_data: Result of ``parse_telephony_websocket`` (dict-like or
            Pipecat ``CallData``). Must expose ``stream_id`` and optionally
            ``call_id``.
        account_sid: Twilio account SID. Defaults to ``TWILIO_ACCOUNT_SID``.
        auth_token: Twilio auth token. Defaults to ``TWILIO_AUTH_TOKEN``.

    Returns:
        Configured :class:`TwilioFrameSerializer`.

    Raises:
        ValueError: If ``stream_id`` / ``stream_sid`` is missing.
    """
    stream_sid = (
        _get(call_data, "stream_id")
        or _get(call_data, "stream_sid")
        or ""
    )
    if not stream_sid:
        raise ValueError("Twilio call data missing stream_id / streamSid")

    call_sid = _get(call_data, "call_id") or _get(call_data, "call_sid")
    sid = account_sid if account_sid is not None else os.getenv("TWILIO_ACCOUNT_SID")
    token = auth_token if auth_token is not None else os.getenv("TWILIO_AUTH_TOKEN")

    can_hang_up = bool(call_sid and sid and token)
    if not can_hang_up:
        logger.warning(
            "Twilio auto_hang_up disabled (need call_sid + TWILIO_ACCOUNT_SID + "
            "TWILIO_AUTH_TOKEN); stream_sid=%s",
            stream_sid,
        )
        return TwilioFrameSerializer(
            stream_sid=str(stream_sid),
            call_sid=str(call_sid) if call_sid else None,
            params=TwilioFrameSerializer.InputParams(auto_hang_up=False),
        )

    return TwilioFrameSerializer(
        stream_sid=str(stream_sid),
        call_sid=str(call_sid),
        account_sid=str(sid),
        auth_token=str(token),
    )


def resolve_session_token(
    *,
    query_token: Optional[str],
    call_data: Mapping[str, Any] | Any | None,
) -> Optional[str]:
    """Resolve the voice session JWT from query string or Stream parameters.

    Twilio Media Streams sometimes drop or omit query parameters on the
    WebSocket URL. The backend also sends ``token`` as a ``<Parameter>``, which
    arrives in ``call_data.body`` after ``parse_telephony_websocket``.

    Args:
        query_token: Optional ``?token=`` from the WebSocket URL.
        call_data: Parsed telephony handshake (may be None before parse).

    Returns:
        Non-empty token string, or ``None`` if neither source has one.
    """
    if query_token and query_token.strip():
        return query_token.strip()

    if call_data is None:
        return None

    body = _get(call_data, "body") or {}
    if isinstance(body, Mapping):
        param = body.get("token")
        if isinstance(param, str) and param.strip():
            return param.strip()
    return None


def _get(obj: Any, key: str) -> Any:
    """Read a key from a mapping or attribute-bearing CallData object."""
    if isinstance(obj, Mapping):
        return obj.get(key)
    return getattr(obj, key, None)
