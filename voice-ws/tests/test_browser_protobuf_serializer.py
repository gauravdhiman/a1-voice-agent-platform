"""Tests for browser-safe WebSocket protobuf serialization."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

from pipecat.frames.frames import (
    InputAudioRawFrame,
    InterruptionFrame,
    LLMTextFrame,
    OutputAudioRawFrame,
    OutputTransportMessageFrame,
    TextFrame,
    TranscriptionFrame,
    TTSAudioRawFrame,
)
from pipecat.serializers.protobuf import ProtobufFrameSerializer

from src.serialization.browser_protobuf import (
    BrowserWebSocketFrameSerializer,
    _protobuf_frame_kind,
)


def _serialize(frame):
    return asyncio.run(BrowserWebSocketFrameSerializer().serialize(frame))


class TestBrowserWebSocketFrameSerializer:
    """Pipeline frames must not break @pipecat-ai/websocket-transport clients."""

    def test_tts_audio_is_serialized_as_output_audio(self) -> None:
        """TTSAudioRawFrame must become protobuf audio (subclass is not enough)."""
        payload = _serialize(
            TTSAudioRawFrame(audio=b"\x01\x02", sample_rate=24000, num_channels=1)
        )
        assert isinstance(payload, bytes)
        frame = asyncio.run(ProtobufFrameSerializer().deserialize(payload))
        assert isinstance(frame, (OutputAudioRawFrame, InputAudioRawFrame))
        assert frame.audio == b"\x01\x02"

    def test_output_audio_still_serializes(self) -> None:
        """Realtime Gemini path must remain unchanged."""
        payload = _serialize(
            OutputAudioRawFrame(audio=b"\x03\x04", sample_rate=16000, num_channels=1)
        )
        assert isinstance(payload, bytes)

    def test_transcription_is_dropped(self) -> None:
        """STT transcription must not reach the browser protobuf decoder."""
        assert (
            _serialize(
                TranscriptionFrame(text="hello", user_id="u", timestamp="now")
            )
            is None
        )

    def test_text_frame_is_dropped(self) -> None:
        """LLM text must not reach the browser protobuf decoder."""
        assert _serialize(TextFrame(text="hello")) is None
        assert _serialize(LLMTextFrame(text="hello")) is None

    def test_interruption_is_dropped(self) -> None:
        """Interruption protobuf uses field 5 which the JS client cannot decode."""
        assert _serialize(InterruptionFrame()) is None

    def test_post_serialize_whitelist_drops_interruption_bytes(self) -> None:
        """Bytes that encode interruption must not reach the browser."""
        interruption_bytes = asyncio.run(
            ProtobufFrameSerializer().serialize(InterruptionFrame())
        )
        assert interruption_bytes is not None
        assert _protobuf_frame_kind(interruption_bytes) == "interruption"

        ser = BrowserWebSocketFrameSerializer()
        with patch.object(
            ser._inner, "serialize", new=AsyncMock(return_value=interruption_bytes)
        ):
            payload = asyncio.run(
                ser.serialize(
                    OutputTransportMessageFrame(
                        message={"label": "rtvi-ai", "type": "bot-started-speaking"}
                    )
                )
            )
        assert payload is None

    def test_rtvi_message_still_serializes(self) -> None:
        """RTVI transport messages must continue to work for speaking events."""
        payload = _serialize(
            OutputTransportMessageFrame(
                message={"label": "rtvi-ai", "type": "bot-started-speaking"}
            )
        )
        assert isinstance(payload, bytes)
