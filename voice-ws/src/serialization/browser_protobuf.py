"""Protobuf serialization compatible with the browser WebSocket transport.

The JavaScript ``@pipecat-ai/websocket-transport`` client only deserializes
``audio`` and ``message`` protobuf frame kinds. Pipeline mode emits additional
frame types (``TTSAudioRawFrame``, ``TranscriptionFrame``, ``TextFrame``,
``InterruptionFrame``) that must be converted or dropped before they reach the
browser. Realtime Gemini Live already emits ``OutputAudioRawFrame`` and RTVI
messages, so this wrapper is a no-op for that path aside from the shared
``OutputAudioRawFrame`` subclass conversion guard.

The inner :class:`~pipecat.serializers.protobuf.ProtobufFrameSerializer` uses
exact-type matching, so audio subclasses must be normalized. A post-serialize
protobuf whitelist catches any frame that still encodes as ``text``,
``transcription``, or ``interruption`` (field 5 is ignored by the JS decoder and
surfaces as ``Unknown frame kind``).
"""

from __future__ import annotations

import logging

import pipecat.frames.protobufs.frames_pb2 as frame_protos
from pipecat.frames.frames import (
    Frame,
    InterruptionFrame,
    OutputAudioRawFrame,
    TextFrame,
    TranscriptionFrame,
)
from pipecat.serializers.base_serializer import FrameSerializer
from pipecat.serializers.protobuf import ProtobufFrameSerializer

logger = logging.getLogger(__name__)

# Frame kinds the browser client cannot decode (see websocket-transport
# ProtobufFrameSerializer.deserialize — only audio + message).
_BROWSER_UNSUPPORTED = (TextFrame, TranscriptionFrame, InterruptionFrame)
_BROWSER_PROTOBUF_KINDS = frozenset({"audio", "message"})
_PROTOBUF_FIELD_NAMES = ("text", "audio", "transcription", "message", "interruption")


def _protobuf_frame_kind(payload: bytes) -> str | None:
    """Return the protobuf oneof field name encoded in a serialized frame."""
    proto = frame_protos.Frame()
    proto.ParseFromString(payload)
    for name in _PROTOBUF_FIELD_NAMES:
        if proto.HasField(name):
            return name
    return None


def _normalize_output_audio(frame: Frame) -> Frame:
    """Coerce ``OutputAudioRawFrame`` subclasses to the exact serializable type."""
    if isinstance(frame, OutputAudioRawFrame) and type(frame) is not OutputAudioRawFrame:
        return OutputAudioRawFrame(
            audio=frame.audio,
            sample_rate=frame.sample_rate,
            num_channels=frame.num_channels,
        )
    return frame


class BrowserWebSocketFrameSerializer(FrameSerializer):
    """Wrap Pipecat protobuf serialization for browser WebSocket clients."""

    def __init__(self, params: FrameSerializer.InputParams | None = None) -> None:
        super().__init__(params)
        self._inner = ProtobufFrameSerializer(params)

    async def serialize(self, frame: Frame) -> str | bytes | None:
        """Serialize a frame for the browser, converting or dropping as needed."""
        frame = _normalize_output_audio(frame)
        if isinstance(frame, _BROWSER_UNSUPPORTED):
            return None

        payload = await self._inner.serialize(frame)
        if not payload or not isinstance(payload, (bytes, bytearray)):
            return payload

        kind = _protobuf_frame_kind(bytes(payload))
        if kind not in _BROWSER_PROTOBUF_KINDS:
            logger.debug(
                "Dropped browser-incompatible protobuf frame kind: %s", kind
            )
            return None
        return payload

    async def deserialize(self, data: str | bytes) -> Frame | None:
        """Deserialize browser-originated protobuf frames."""
        return await self._inner.deserialize(data)
