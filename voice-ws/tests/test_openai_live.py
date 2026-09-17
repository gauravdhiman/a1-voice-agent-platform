"""Protocol and frame-contract tests for the GPT-Live Pipecat adapter."""

from __future__ import annotations

import base64
import json
from collections import deque
from unittest.mock import AsyncMock

import pytest
from pipecat.frames.frames import TTSAudioRawFrame
from src.speech.openai_live import OPENAI_LIVE_URL, OpenAILiveLLMService


class FakeWebSocket:
    """Small async WebSocket double that records commands and emits events."""

    def __init__(self, events: list[dict] | None = None) -> None:
        self.events = deque(json.dumps(event) for event in events or [])
        self.sent: list[dict] = []
        self.closed = False

    async def send(self, payload: str) -> None:
        self.sent.append(json.loads(payload))

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self.events:
            raise StopAsyncIteration
        return self.events.popleft()

    async def close(self) -> None:
        self.closed = True


@pytest.mark.asyncio
async def test_connect_sends_session_start_and_waits_for_started() -> None:
    websocket = FakeWebSocket([{"type": "session.started"}])

    async def connect(uri: str, **kwargs):
        assert uri == OPENAI_LIVE_URL
        assert kwargs["additional_headers"] == {"Authorization": "Bearer secret"}
        return websocket

    service = OpenAILiveLLMService(
        api_key="secret",
        model="gpt-live-1",
        voice="marin",
        system_instruction="system prompt",
        websocket_factory=connect,
        connection_timeout=1,
        close_timeout=0.01,
    )

    await service._connect()

    assert websocket.sent[0]["type"] == "session.start"
    assert websocket.sent[0]["session"]["model"] == "gpt-live-1"
    assert websocket.sent[0]["session"]["audio"]["format"] == {
        "type": "audio/pcm",
        "rate": 24000,
    }
    assert (
        websocket.sent[0]["session"]["delegation"]["responses"]["instructions"]
        == "system prompt"
    )
    await service._disconnect()


@pytest.mark.asyncio
async def test_output_audio_is_resampled_to_pipeline_rate() -> None:
    service = OpenAILiveLLMService(
        api_key="secret",
        model="gpt-live-1",
        voice="marin",
        system_instruction="prompt",
    )
    service._started.set()
    service._output_sample_rate = 16000
    service.push_frame = AsyncMock()
    audio = base64.b64encode(b"\x01\x00" * 2400).decode("ascii")

    await service._handle_event({"type": "session.output_audio.delta", "delta": audio})

    emitted = [call.args[0] for call in service.push_frame.await_args_list]
    audio_frames = [frame for frame in emitted if isinstance(frame, TTSAudioRawFrame)]
    assert len(audio_frames) == 1
    assert audio_frames[0].sample_rate == 16000
    assert audio_frames[0].num_channels == 1
    assert audio_frames[0].audio


@pytest.mark.asyncio
async def test_backend_response_completion_does_not_end_live_audio() -> None:
    """Responses completion is independent from GPT-Live audio playback."""
    service = OpenAILiveLLMService(
        api_key="secret",
        model="gpt-live-1",
        voice="marin",
        system_instruction="prompt",
    )
    service._speech_active = True
    service.push_frame = AsyncMock()

    await service._handle_event(
        {
            "type": "response.event",
            "event": {"type": "response.completed"},
        }
    )

    assert service._speech_active is True
    service.push_frame.assert_not_awaited()


@pytest.mark.asyncio
async def test_only_nested_completed_function_calls_execute_and_resume_once() -> None:
    websocket = FakeWebSocket()
    service = OpenAILiveLLMService(
        api_key="secret",
        model="gpt-live-1",
        voice="marin",
        system_instruction="prompt",
    )
    service._websocket = websocket
    service._started.set()
    service.register_function("lookup", AsyncMock())

    async def run_function_calls(calls) -> None:
        call_id = calls[0].tool_call_id
        service._tool_results[call_id] = {"status": "ok"}
        service._tool_result_events[call_id].set()

    service.run_function_calls = AsyncMock(side_effect=run_function_calls)
    item = {
        "type": "function_call",
        "call_id": "call_1",
        "name": "lookup",
        "arguments": '{"query":"Phoenix"}',
    }

    await service._handle_event({"type": "response.output_item.done", "item": item})
    assert websocket.sent == []

    await service._handle_event(
        {
            "type": "response.event",
            "event": {"type": "response.output_item.done", "item": item},
        }
    )
    await service._handle_event(
        {
            "type": "response.event",
            "event": {"type": "response.output_item.done", "item": item},
        }
    )

    assert [event["type"] for event in websocket.sent] == [
        "response.item.create",
        "response.create",
    ]
    assert websocket.sent[0]["item"]["output"] == '{"status": "ok"}'
    service.run_function_calls.assert_awaited_once()


@pytest.mark.asyncio
async def test_greeting_uses_acknowledged_instruction_and_commentary_events() -> None:
    websocket = FakeWebSocket()
    service = OpenAILiveLLMService(
        api_key="secret",
        model="gpt-live-1",
        voice="marin",
        system_instruction="prompt",
        command_timeout=1,
    )
    service._websocket = websocket
    service._started.set()

    async def acknowledge(event_type: str) -> None:
        event = websocket.sent[-1]
        await service._handle_event(
            {
                "type": f"{event_type}d",
                "client_event_id": event["event_id"],
            }
        )

    original_send = service._send

    async def send_and_ack(event, **kwargs):
        await original_send(event, **kwargs)
        if event["type"] == "session.instructions.append":
            await acknowledge("session.instructions.appende")
        elif event["type"] == "session.commentary.append":
            await acknowledge("session.commentary.appende")

    service._send = send_and_ack
    await service.send_greeting("Greet now.")

    assert [event["type"] for event in websocket.sent] == [
        "session.instructions.append",
        "session.commentary.append",
    ]
    assert websocket.sent[0]["content"] == "Greet now."
    assert websocket.sent[1]["content"] == "Begin the conversation now."
