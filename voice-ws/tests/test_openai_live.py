"""Protocol and frame-contract tests for the GPT-Live Pipecat adapter."""

from __future__ import annotations

import base64
import json
import math
from collections import deque
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from pipecat.frames.frames import (
    InterruptionFrame,
    LLMFullResponseStartFrame,
    TranscriptionFrame,
    TTSAudioRawFrame,
)
from pipecat.processors.frame_processor import FrameDirection
from pipecat.utils.asyncio.task_manager import TaskManager
from src.speech.openai_live import (
    OPENAI_LIVE_URL,
    OpenAILiveError,
    OpenAILiveLLMService,
)
from websockets.exceptions import ConnectionClosedOK


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
    websocket = FakeWebSocket(
        [
            {"type": "session.started"},
            {"type": "session.closed", "reason": "close_requested"},
        ]
    )

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
async def test_clean_eof_before_session_started_fails_startup() -> None:
    websocket = FakeWebSocket()

    async def connect(_uri: str, **_kwargs):
        return websocket

    service = OpenAILiveLLMService(
        api_key="secret",
        model="gpt-live-1",
        voice="marin",
        system_instruction="prompt",
        websocket_factory=connect,
        connection_timeout=1,
        close_timeout=0.01,
    )

    with pytest.raises(OpenAILiveError):
        await service._connect()

    assert service._session_ready is False
    assert service._fatal_error is not None
    assert service._fatal_error.code == "connection_closed"
    assert websocket.closed is True


@pytest.mark.asyncio
async def test_clean_eof_after_session_started_fails_startup() -> None:
    websocket = FakeWebSocket([{"type": "session.started"}])

    async def connect(_uri: str, **_kwargs):
        return websocket

    service = OpenAILiveLLMService(
        api_key="secret",
        model="gpt-live-1",
        voice="marin",
        system_instruction="prompt",
        websocket_factory=connect,
        connection_timeout=1,
        close_timeout=0.01,
    )

    with pytest.raises(OpenAILiveError) as error:
        await service._connect()

    assert error.value.code == "session_finalization_unconfirmed"
    assert service._session_ready is True
    assert service._fatal_error is not None
    assert service._fatal_error.code == "session_finalization_unconfirmed"
    assert websocket.closed is True


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
async def test_input_transcript_fragments_accumulate_upstream() -> None:
    """Live input fragments finalize before the realtime assistant handoff."""
    service = OpenAILiveLLMService(
        api_key="secret",
        model="gpt-live-1",
        voice="marin",
        system_instruction="prompt",
    )
    service.push_frame = AsyncMock()

    await service._handle_event(
        {
            "type": "session.input_transcript.delta",
            "delta": "Hello ",
            "start_ms": 100,
            "end_ms": 200,
        }
    )
    await service._handle_event(
        {
            "type": "session.input_transcript.delta",
            "delta": "there",
            "start_ms": 200,
            "end_ms": 300,
        }
    )

    await service._handle_event(
        {
            "type": "session.output_transcript.delta",
            "delta": "Hi there.",
            "start_ms": 300,
            "end_ms": 500,
        }
    )

    frames = [call.args[0] for call in service.push_frame.await_args_list]
    assert isinstance(frames[0], TranscriptionFrame)
    assert frames[0].text == "Hello there"
    assert frames[0].finalized is True
    assert (
        service.push_frame.await_args_list[0].kwargs["direction"]
        == FrameDirection.UPSTREAM
    )
    assert isinstance(frames[1], LLMFullResponseStartFrame)


@pytest.mark.asyncio
async def test_each_live_turn_hands_off_ordered_input_transcript_once() -> None:
    """A later Live turn is not held behind delegated Responses completion."""
    service = OpenAILiveLLMService(
        api_key="secret",
        model="gpt-live-1",
        voice="marin",
        system_instruction="prompt",
    )
    service.push_frame = AsyncMock()

    events = [
        {
            "type": "session.input_transcript.delta",
            "delta": "First turn",
            "start_ms": 100,
            "end_ms": 300,
        },
        {
            "type": "session.output_transcript.delta",
            "delta": "First reply",
            "start_ms": 300,
            "end_ms": 600,
        },
        {
            "type": "session.input_transcript.delta",
            "delta": "Second turn",
            "start_ms": 1800,
            "end_ms": 2000,
        },
        {
            "type": "session.output_transcript.delta",
            "delta": "Second reply",
            "start_ms": 2000,
            "end_ms": 2300,
        },
    ]
    for event in events:
        await service._handle_event(event)

    frames = [call.args[0] for call in service.push_frame.await_args_list]
    transcripts = [
        frame.text for frame in frames if isinstance(frame, TranscriptionFrame)
    ]
    response_starts = [
        frame for frame in frames if isinstance(frame, LLMFullResponseStartFrame)
    ]
    assert transcripts == ["First turn", "Second turn"]
    assert len(response_starts) == 2
    assert service._input_transcript_fragments == []


@pytest.mark.asyncio
async def test_metadata_free_rapid_turn_is_rejected_without_a_handoff_boundary() -> (
    None
):
    """Missing provider intervals cannot be classified from event arrival order."""
    service = OpenAILiveLLMService(
        api_key="secret",
        model="gpt-live-1",
        voice="marin",
        system_instruction="prompt",
    )
    service.push_frame = AsyncMock()
    service.push_error = AsyncMock()

    await service._handle_event(
        {
            "type": "session.input_transcript.delta",
            "delta": "First turn",
            "start_ms": 100,
            "end_ms": 300,
        }
    )
    await service._handle_event(
        {
            "type": "session.output_transcript.delta",
            "delta": "First reply",
            "start_ms": 300,
            "end_ms": 600,
        }
    )
    await service._handle_event(
        {"type": "session.input_transcript.delta", "delta": "Second turn"}
    )
    await service._handle_event(
        {"type": "session.output_transcript.delta", "delta": "Second reply"}
    )

    frames = [call.args[0] for call in service.push_frame.await_args_list]
    assert [
        frame.text for frame in frames if isinstance(frame, TranscriptionFrame)
    ] == ["First turn"]
    assert sum(isinstance(frame, LLMFullResponseStartFrame) for frame in frames) == 1
    assert service._fatal_error is not None
    assert service._fatal_error.code == "missing_transcript_timeline"
    service.push_error.assert_awaited()


@pytest.mark.asyncio
async def test_late_input_fragment_does_not_reopen_response_handoff() -> None:
    """A delayed input fragment joins the open user handoff exactly once."""
    service = OpenAILiveLLMService(
        api_key="secret",
        model="gpt-live-1",
        voice="marin",
        system_instruction="prompt",
    )
    service.push_frame = AsyncMock()

    events = [
        {
            "type": "session.input_transcript.delta",
            "delta": "Hello",
            "start_ms": 100,
            "end_ms": 300,
        },
        {
            "type": "session.output_transcript.delta",
            "delta": "Hi",
            "start_ms": 300,
            "end_ms": 600,
        },
        {
            "type": "session.input_transcript.delta",
            "delta": " there",
            "start_ms": 250,
            "end_ms": 350,
        },
        {
            "type": "session.output_transcript.delta",
            "delta": " there",
            "start_ms": 500,
            "end_ms": 700,
        },
    ]
    for event in events:
        await service._handle_event(event)

    frames = [call.args[0] for call in service.push_frame.await_args_list]
    assert [
        frame.text for frame in frames if isinstance(frame, TranscriptionFrame)
    ] == [
        "Hello",
        " there",
    ]
    assert sum(isinstance(frame, LLMFullResponseStartFrame) for frame in frames) == 1


@pytest.mark.asyncio
async def test_interruption_preserves_the_next_timestamped_turn() -> None:
    """An interruption resets response state without orphaning accepted input."""
    service = OpenAILiveLLMService(
        api_key="secret",
        model="gpt-live-1",
        voice="marin",
        system_instruction="prompt",
    )
    service.push_frame = AsyncMock()

    events = [
        {
            "type": "session.input_transcript.delta",
            "delta": "First turn",
            "start_ms": 100,
            "end_ms": 300,
        },
        {
            "type": "session.output_transcript.delta",
            "delta": "First reply",
            "start_ms": 300,
            "end_ms": 600,
        },
        {
            "type": "session.input_transcript.delta",
            "delta": "Interrupted turn",
            "start_ms": 1800,
            "end_ms": 2000,
        },
        {"type": "session.interrupted"},
        {
            "type": "session.output_transcript.delta",
            "delta": "Second reply",
            "start_ms": 2000,
            "end_ms": 2300,
        },
    ]
    for event in events:
        await service._handle_event(event)

    frames = [call.args[0] for call in service.push_frame.await_args_list]
    assert [
        frame.text for frame in frames if isinstance(frame, TranscriptionFrame)
    ] == ["First turn", "Interrupted turn"]
    assert sum(isinstance(frame, LLMFullResponseStartFrame) for frame in frames) == 2
    assert sum(isinstance(frame, InterruptionFrame) for frame in frames) == 1


@pytest.mark.asyncio
async def test_overlapping_input_interval_does_not_start_second_response() -> None:
    """A user interval overlapping assistant speech remains one exchange."""
    service = OpenAILiveLLMService(
        api_key="secret",
        model="gpt-live-1",
        voice="marin",
        system_instruction="prompt",
    )
    service.push_frame = AsyncMock()

    await service._handle_event(
        {
            "type": "session.input_transcript.delta",
            "delta": "Actually",
            "start_ms": 1000,
            "end_ms": 1200,
        }
    )
    await service._handle_event(
        {
            "type": "session.output_transcript.delta",
            "delta": "Sure",
            "start_ms": 1200,
            "end_ms": 1600,
        }
    )
    await service._handle_event(
        {
            "type": "session.input_transcript.delta",
            "delta": " wait",
            "start_ms": 1450,
            "end_ms": 1750,
        }
    )
    await service._handle_event(
        {
            "type": "session.output_transcript.delta",
            "delta": " one moment",
            "start_ms": 1600,
            "end_ms": 1900,
        }
    )

    frames = [call.args[0] for call in service.push_frame.await_args_list]
    assert [
        frame.text for frame in frames if isinstance(frame, TranscriptionFrame)
    ] == [
        "Actually",
        " wait",
    ]
    assert sum(isinstance(frame, LLMFullResponseStartFrame) for frame in frames) == 1


@pytest.mark.asyncio
async def test_backend_response_completion_does_not_fabricate_audio_lifecycle() -> None:
    """Live has no audio-done event, so backend completion emits no fake bracket."""
    service = OpenAILiveLLMService(
        api_key="secret",
        model="gpt-live-1",
        voice="marin",
        system_instruction="prompt",
    )
    service.push_frame = AsyncMock()

    await service._handle_event(
        {
            "type": "response.event",
            "event": {"type": "response.completed"},
        }
    )

    service.push_frame.assert_not_awaited()


@pytest.mark.asyncio
async def test_usage_snapshots_are_validated_cumulative_and_retained() -> None:
    """Live and nested Responses usage is retained without double-counting snapshots."""
    service = OpenAILiveLLMService(
        api_key="secret",
        model="gpt-live-1",
        voice="marin",
        system_instruction="prompt",
    )
    service.start_llm_usage_metrics = AsyncMock()

    with (
        patch("src.speech.openai_live.record") as record,
        patch("src.speech.openai_live.event") as usage_event,
    ):
        await service._handle_event(
            {
                "type": "session.usage.updated",
                "usage": {
                    "seconds": 10.0,
                    "input_tokens": 100,
                    "output_tokens": 20,
                    "input_token_details": {"audio_tokens": 8},
                    "untrusted": 999,
                    "seconds_invalid": math.nan,
                },
            }
        )
        await service._handle_event(
            {
                "type": "session.usage.updated",
                "usage": {
                    "seconds": 15.0,
                    "input_tokens": 130,
                    "output_tokens": 35,
                    "input_token_details": {"audio_tokens": 10},
                },
            }
        )
        response_event = {
            "type": "response.event",
            "event": {
                "type": "response.completed",
                "response": {
                    "id": "resp_1",
                    "usage": {"input_tokens": 4, "output_tokens": 3},
                },
            },
        }
        await service._handle_event(response_event)
        await service._handle_event(response_event)

    assert service.usage_snapshot["live"] == {
        "seconds": 15.0,
        "input_tokens": 130,
        "output_tokens": 35,
        "input_audio_tokens": 10,
    }
    assert service.usage_snapshot["responses"]["resp_1"] == {
        "input_tokens": 4,
        "output_tokens": 3,
    }
    assert [call.args[1] for call in record.call_args_list] == [10.0, 5.0]
    assert [call.kwargs["audio_seconds"] for call in usage_event.call_args_list] == [
        10.0,
        5.0,
    ]
    assert service.start_llm_usage_metrics.await_count == 3


@pytest.mark.asyncio
async def test_terminal_usage_is_retained_and_marks_finalization_confirmed() -> None:
    """The terminal close snapshot is retained before a successful close."""
    service = OpenAILiveLLMService(
        api_key="secret",
        model="gpt-live-1",
        voice="marin",
        system_instruction="prompt",
    )
    service.start_llm_usage_metrics = AsyncMock()

    await service._handle_event(
        {
            "type": "session.closed",
            "reason": "close_requested",
            "usage": {"seconds": 12.5, "input_tokens": 40, "output_tokens": 9},
        }
    )

    assert service.usage_snapshot == {
        "live": {"seconds": 12.5, "input_tokens": 40, "output_tokens": 9},
        "responses": {},
        "finalized": True,
    }
    service.start_llm_usage_metrics.assert_awaited_once()


@pytest.mark.asyncio
async def test_peer_close_before_session_closed_is_unconfirmed() -> None:
    """A peer close during teardown cannot be treated as confirmed finalization."""

    class PeerCloseWebSocket(FakeWebSocket):
        async def __anext__(self):
            raise ConnectionClosedOK(None, None)

    service = OpenAILiveLLMService(
        api_key="secret",
        model="gpt-live-1",
        voice="marin",
        system_instruction="prompt",
    )
    service._websocket = PeerCloseWebSocket()
    service._closing = True
    service.push_error = AsyncMock()

    await service._receive_events()

    assert service._fatal_error is not None
    assert service._fatal_error.code == "session_finalization_unconfirmed"
    assert service.finalization_failure_code == "session_finalization_unconfirmed"


@pytest.mark.asyncio
async def test_session_closed_connection_loss_is_unconfirmed() -> None:
    """A provider connection-loss close cannot be reported as a completed call."""
    service = OpenAILiveLLMService(
        api_key="secret",
        model="gpt-live-1",
        voice="marin",
        system_instruction="prompt",
    )
    service.push_error = AsyncMock()

    await service._handle_event({"type": "session.closed", "reason": "connection_lost"})

    assert service._fatal_error is not None
    assert service._fatal_error.code == "session_finalization_unconfirmed"
    assert service.finalization_failure_code == "session_finalization_unconfirmed"
    assert service.usage_snapshot["finalized"] is False


@pytest.mark.asyncio
async def test_disconnect_requires_terminal_session_event() -> None:
    """Teardown marks finalization unconfirmed when the provider never closes."""
    websocket = FakeWebSocket()
    service = OpenAILiveLLMService(
        api_key="secret",
        model="gpt-live-1",
        voice="marin",
        system_instruction="prompt",
        close_timeout=0,
    )
    service._websocket = websocket
    service._session_ready = True
    service.push_error = AsyncMock()

    await service._disconnect()

    assert websocket.sent[0]["type"] == "session.close"
    assert service._fatal_error is not None
    assert service._fatal_error.code == "session_finalization_unconfirmed"
    assert service.finalization_failure_code == "session_finalization_unconfirmed"


@pytest.mark.asyncio
async def test_disconnect_records_session_close_send_failure() -> None:
    """A failed close command is retained as an unconfirmed finalization."""

    class FailingSessionCloseWebSocket(FakeWebSocket):
        async def send(self, payload: str) -> None:
            event = json.loads(payload)
            if event["type"] == "session.close":
                raise RuntimeError("close rejected")
            await super().send(payload)

    service = OpenAILiveLLMService(
        api_key="secret",
        model="gpt-live-1",
        voice="marin",
        system_instruction="prompt",
        close_timeout=0,
    )
    service._websocket = FailingSessionCloseWebSocket()
    service._session_ready = True
    service.push_error = AsyncMock()

    await service._disconnect()

    assert service._fatal_error is not None
    assert service._fatal_error.code == "session_finalization_unconfirmed"
    assert service.finalization_failure_code == "session_finalization_unconfirmed"


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
    service._session_ready = True
    service._task_manager = TaskManager()
    service._setup = SimpleNamespace(
        pipeline_worker=SimpleNamespace(app_resources=None, worker_runner=None)
    )
    service.broadcast_frame = AsyncMock()
    handler_calls = []

    async def handler(params) -> None:
        handler_calls.append(params)
        await params.result_callback({"status": "ok"})

    service.register_function("lookup", handler)
    await service._create_sequential_runner_task()
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
    assert len(handler_calls) == 1
    assert handler_calls[0].function_name == "lookup"
    assert handler_calls[0].tool_call_id == "call_1"
    assert handler_calls[0].arguments == {"query": "Phoenix"}
    await service._cancel_sequential_runner_task()


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
    service._session_ready = True

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
