"""Pipecat adapter for OpenAI GPT-Live's server-to-server WebSocket API."""

from __future__ import annotations

import asyncio
import base64
import copy
import json
import logging
import math
import uuid
from collections.abc import Awaitable, Callable, Mapping
from contextlib import suppress
from typing import Any

from pipecat.adapters.schemas.tools_schema import ToolsSchema
from pipecat.audio.utils import create_stream_resampler
from pipecat.frames.frames import (
    AggregationType,
    Frame,
    InputAudioRawFrame,
    InterruptionFrame,
    LLMContextFrame,
    LLMFullResponseStartFrame,
    LLMServiceMetadataFrame,
    LLMTextFrame,
    TranscriptionFrame,
    TTSAudioRawFrame,
    TTSTextFrame,
)
from pipecat.metrics.metrics import LLMTokenUsage
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.frame_processor import FrameDirection, FrameProcessorSetup
from pipecat.services.llm_service import FunctionCallFromLLM, LLMService, LLMSettings
from pipecat.utils.time import time_now_iso8601
from websockets.asyncio.client import connect as websocket_connect
from websockets.exceptions import ConnectionClosed

from shared.observability.signals import event, record

logger = logging.getLogger(__name__)

OPENAI_LIVE_URL = "wss://api.openai.com/v1/live/sessions"
OPENAI_LIVE_AUDIO_RATE = 24000
OPENAI_LIVE_BACKEND_MODEL = "gpt-4.1"
DEFAULT_OUTPUT_SAMPLE_RATE = 16000
DEFAULT_CLOSE_TIMEOUT_SECONDS = 15.0
DEFAULT_COMMAND_TIMEOUT_SECONDS = 15.0
DEFAULT_TOOL_TIMEOUT_SECONDS = 60.0
MAX_SAFE_USAGE_VALUE = 10**12
_SUCCESSFUL_CLOSE_REASONS = {"close_requested", "remote_hangup", "expired"}


class OpenAILiveError(RuntimeError):
    """Safe runtime error for an OpenAI Live connection or protocol failure."""

    def __init__(self, message: str, *, code: str = "provider_error") -> None:
        super().__init__(message)
        self.code = code


WebSocketFactory = Callable[..., Awaitable[Any]]


def _responses_tools(tools: ToolsSchema | None) -> list[dict[str, Any]]:
    """Convert Pipecat function schemas to Responses function definitions."""
    if tools is None:
        return []
    result = []
    for schema in tools.standard_tools:
        definition = schema.to_default_dict()
        result.append(
            {
                "type": "function",
                "name": definition["name"],
                "description": definition["description"],
                "parameters": definition["parameters"],
            }
        )
    return result


class OpenAILiveLLMService(LLMService[Any]):
    """Bridge Pipecat frames and a GPT-Live audio/delegation session.

    GPT-Live owns the speech-to-speech turn loop. The service therefore sends
    audio directly after the session handshake and only uses Pipecat's LLM
    function registry when a delegated Responses event completes a function
    call. Live does not provide an output-audio-done event, so audio is a
    continuous stream: interruption frames are the playback boundary and the
    adapter does not invent per-response TTS brackets from backend completion.
    """

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        voice: str,
        system_instruction: str,
        tools: ToolsSchema | None = None,
        websocket_factory: WebSocketFactory | None = None,
        connection_timeout: float = DEFAULT_COMMAND_TIMEOUT_SECONDS,
        command_timeout: float = DEFAULT_COMMAND_TIMEOUT_SECONDS,
        tool_timeout: float = DEFAULT_TOOL_TIMEOUT_SECONDS,
        close_timeout: float = DEFAULT_CLOSE_TIMEOUT_SECONDS,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            run_in_parallel=False,
            group_parallel_tools=False,
            function_call_timeout_secs=tool_timeout,
            settings=LLMSettings(
                model=model,
                system_instruction=system_instruction,
                temperature=None,
                max_tokens=None,
                top_p=None,
                top_k=None,
                frequency_penalty=None,
                presence_penalty=None,
                seed=None,
                filter_incomplete_user_turns=False,
                user_turn_completion_config=None,
            ),
            **kwargs,
        )
        self._api_key = api_key
        self._model = model
        self._voice = voice
        self._system_instruction = system_instruction
        self._tools = tools
        self._websocket_factory = websocket_factory or websocket_connect
        self._connection_timeout = connection_timeout
        self._command_timeout = command_timeout
        self._tool_timeout = tool_timeout
        self._close_timeout = close_timeout
        self._websocket: Any | None = None
        self._receive_task: asyncio.Task[None] | None = None
        self._send_lock = asyncio.Lock()
        self._started = asyncio.Event()
        self._closed = asyncio.Event()
        self._fatal_error: OpenAILiveError | None = None
        self._closing = False
        self._session_ready = False
        self._closed_reason: str | None = None
        self._ack_waiters: dict[str, asyncio.Future[dict[str, Any]]] = {}
        self._context: LLMContext | None = None
        self._input_resampler = create_stream_resampler()
        self._output_resampler = create_stream_resampler()
        self._output_sample_rate = DEFAULT_OUTPUT_SAMPLE_RATE
        self._input_transcript_fragments: list[str] = []
        self._response_started = False
        self._seen_tool_calls: set[str] = set()
        self._submitted_tool_calls: set[str] = set()
        self._tool_results: dict[str, Any] = {}
        self._tool_result_events: dict[str, asyncio.Event] = {}
        self._usage_snapshots: dict[str, dict[str, Any]] = {
            "live": {},
            "responses": {},
        }
        self._response_usage_snapshots: dict[str, dict[str, Any]] = {}

    def service_metadata_frame(self) -> LLMServiceMetadataFrame:
        """Declare a continuous realtime service without provider turn frames."""
        self._warn_if_realtime_service_emits_no_turn_frames(emits_turn_frames=False)
        return LLMServiceMetadataFrame(
            service_name=self.name,
            is_realtime_service=True,
        )

    @property
    def usage_snapshot(self) -> dict[str, Any]:
        """Return the latest validated provider usage without raw payloads."""
        return {
            "live": dict(self._usage_snapshots["live"]),
            "responses": {
                key: dict(value)
                for key, value in self._response_usage_snapshots.items()
            },
            "finalized": self._closed.is_set()
            and self._closed_reason in _SUCCESSFUL_CLOSE_REASONS,
        }

    @property
    def finalization_failure_code(self) -> str | None:
        """Expose only finalization failure codes to the call tracker."""
        if self._fatal_error is None:
            return None
        if self._fatal_error.code in {
            "provider_session_closed",
            "session_finalization_unconfirmed",
        }:
            return self._fatal_error.code
        return None

    async def setup(self, setup: FrameProcessorSetup) -> None:
        """Connect and complete the GPT-Live startup handshake."""
        await super().setup(setup)
        await self._connect()

    async def cleanup(self) -> None:
        """Close the Live session and release its receive task."""
        await self._disconnect()
        await super().cleanup()

    def register_function(
        self,
        function_name: str | None,
        handler: Any,
        *,
        cancel_on_interruption: bool | None = None,
        timeout_secs: float | None = None,
        cancellable_by_llm: bool | None = None,
    ) -> None:
        """Register a Pipecat handler while capturing its final result safely."""

        async def capture_result(params: Any) -> None:
            forwarded = copy.copy(params)
            original_callback = params.result_callback

            async def result_callback(result: Any, *args: Any, **kwargs: Any) -> None:
                await original_callback(result, *args, **kwargs)
                properties = kwargs.get("properties")
                if properties is None or properties.is_final:
                    self._tool_results[params.tool_call_id] = result
                    waiter = self._tool_result_events.get(params.tool_call_id)
                    if waiter is not None:
                        waiter.set()

            forwarded.result_callback = result_callback
            try:
                await handler(forwarded)
            except Exception:  # noqa: BLE001 - normalize provider tool failures
                if params.tool_call_id not in self._tool_results:
                    self._tool_results[params.tool_call_id] = {
                        "error": "Tool execution failed."
                    }
                    waiter = self._tool_result_events.get(params.tool_call_id)
                    if waiter is not None:
                        waiter.set()
                raise

        super().register_function(
            function_name,
            capture_result,
            cancel_on_interruption=cancel_on_interruption,
            timeout_secs=timeout_secs,
            cancellable_by_llm=cancellable_by_llm,
        )

    async def send_greeting(self, instruction: str) -> None:
        """Ask GPT-Live to greet immediately after the caller connects."""
        await self._wait_until_started()
        await self._append_context("session.instructions.append", instruction)
        await self._append_context(
            "session.commentary.append", "Begin the conversation now."
        )

    async def process_frame(self, frame: Frame, direction: FrameDirection) -> None:
        """Route audio into Live while preserving Pipecat pipeline frames."""
        await super().process_frame(frame, direction)

        if isinstance(frame, LLMContextFrame):
            self._context = frame.context
        elif isinstance(frame, InputAudioRawFrame):
            self._output_sample_rate = frame.sample_rate
            if (
                self._session_ready
                and not self._closing
                and not self._closed.is_set()
                and self._fatal_error is None
            ):
                await self._send_input_audio(frame)

        await self.push_frame(frame, direction)

    async def _connect(self) -> None:
        """Open the socket, start receiving, and wait for session.started."""
        headers = {"Authorization": f"Bearer {self._api_key}"}
        try:
            try:
                self._websocket = await self._websocket_factory(
                    OPENAI_LIVE_URL,
                    additional_headers=headers,
                )
            except TypeError:
                self._websocket = await self._websocket_factory(
                    OPENAI_LIVE_URL,
                    extra_headers=headers,
                )
            self._receive_task = asyncio.create_task(self._receive_events())
            await self._send(self._session_start(), allow_before_start=True)
            await asyncio.wait_for(
                self._started.wait(), timeout=self._connection_timeout
            )
        except asyncio.TimeoutError as exc:
            await self._report_error("session_start_timeout", fatal=True)
            await self._disconnect()
            raise OpenAILiveError("OpenAI Live session did not start in time.") from exc
        except Exception as exc:
            if isinstance(exc, OpenAILiveError):
                await self._disconnect()
                raise
            await self._report_error("connection_failed", fatal=True)
            await self._disconnect()
            raise OpenAILiveError("OpenAI Live connection failed.") from exc

        if self._fatal_error or not self._session_ready:
            if self._fatal_error is None:
                await self._report_error("connection_closed", fatal=True)
            error = self._fatal_error or OpenAILiveError(
                "OpenAI Live session did not become ready.",
                code="connection_closed",
            )
            await self._disconnect()
            raise error

    def _session_start(self) -> dict[str, Any]:
        """Build the fixed Live session and Responses delegation contract."""
        return {
            "type": "session.start",
            "event_id": self._event_id(),
            "session": {
                "model": self._model,
                "instructions": self._system_instruction,
                "audio": {
                    "format": {"type": "audio/pcm", "rate": OPENAI_LIVE_AUDIO_RATE},
                    "output": {"voice": self._voice},
                },
                "delegation": {
                    "type": "responses",
                    "responses": {
                        "model": OPENAI_LIVE_BACKEND_MODEL,
                        "instructions": self._system_instruction,
                        "tools": _responses_tools(self._tools),
                        "tool_choice": "auto",
                        "parallel_tool_calls": False,
                    },
                },
            },
        }

    async def _receive_events(self) -> None:
        """Receive provider events without logging event bodies or credentials."""
        websocket = self._websocket
        if websocket is None:
            return
        try:
            async for raw_event in websocket:
                try:
                    event = json.loads(
                        raw_event.decode("utf-8")
                        if isinstance(raw_event, bytes)
                        else raw_event
                    )
                    if not isinstance(event, dict):
                        raise ValueError("event is not an object")
                    await self._handle_event(event)
                except (TypeError, ValueError, json.JSONDecodeError):
                    await self._report_error("malformed_event", fatal=True)
        except asyncio.CancelledError:
            raise
        except ConnectionClosed:
            if not self._closed.is_set():
                await self._report_error(
                    (
                        "session_finalization_unconfirmed"
                        if self._closing
                        else "connection_closed"
                    ),
                    fatal=True,
                )
        except Exception as exc:  # noqa: BLE001 - provider transport boundary
            if not self._closing or not self._closed.is_set():
                logger.error(
                    "OpenAI Live receive loop failed type=%s",
                    type(exc).__name__,
                )
                await self._report_error(
                    (
                        "session_finalization_unconfirmed"
                        if self._closing
                        else "receive_failed"
                    ),
                    fatal=True,
                )
        else:
            if not self._closed.is_set():
                await self._report_error(
                    (
                        "session_finalization_unconfirmed"
                        if self._session_ready
                        else "connection_closed"
                    ),
                    fatal=True,
                )
        finally:
            if not self._started.is_set():
                self._started.set()

    async def _handle_event(self, event: dict[str, Any]) -> None:
        """Dispatch one safe, already-decoded provider event."""
        event_type = event.get("type")
        self._resolve_ack(event)

        if event_type == "session.started":
            self._session_ready = True
            self._started.set()
            return
        if event_type == "session.usage.updated":
            await self._record_usage(event.get("usage"), source="live")
            return
        if event_type == "session.closed":
            reason = event.get("reason")
            self._closed_reason = reason if isinstance(reason, str) else None
            await self._record_usage(event.get("usage"), source="live")
            self._closed.set()
            if self._closed_reason not in _SUCCESSFUL_CLOSE_REASONS:
                await self._report_error(
                    (
                        "session_finalization_unconfirmed"
                        if self._closed_reason == "connection_lost"
                        else "provider_session_closed"
                    ),
                    fatal=True,
                )
            return
        if event_type == "error":
            error = event.get("error")
            code = error.get("code") if isinstance(error, dict) else None
            await self._report_error(str(code or "provider_error"), fatal=True)
            return
        if event_type == "session.output_audio.delta":
            await self._handle_audio_delta(event.get("delta"))
            return
        if event_type == "session.output_transcript.delta":
            await self._handle_output_text(event.get("delta"))
            return
        if event_type == "session.input_transcript.delta":
            await self._handle_input_text(event.get("delta"))
            return
        if event_type == "session.interrupted":
            self._response_started = False
            await self.push_frame(InterruptionFrame())
            return
        if event_type == "session.delegation.created":
            return
        if event_type == "response.event":
            nested = event.get("event")
            if isinstance(nested, dict):
                await self._handle_response_event(nested)

    async def _handle_response_event(self, event: dict[str, Any]) -> None:
        """Handle only nested Responses events from the configured delegation."""
        event_type = event.get("type")
        if event_type == "response.output_item.done":
            item = event.get("item")
            if isinstance(item, dict) and item.get("type") == "function_call":
                await self._handle_function_call(item)
            return
        if event_type == "response.completed":
            response = event.get("response")
            usage = event.get("usage")
            if usage is None and isinstance(response, dict):
                usage = response.get("usage")
            await self._record_usage(
                usage,
                source="responses",
                identity=self._response_usage_identity(event),
            )

    @staticmethod
    def _response_usage_identity(event: Mapping[str, Any]) -> str:
        """Return a stable, non-sensitive key for one Responses stream."""
        response = event.get("response")
        if isinstance(response, Mapping):
            for key in ("id", "response_id"):
                value = response.get(key)
                if isinstance(value, str) and value:
                    return value
        for key in ("id", "response_id"):
            value = event.get(key)
            if isinstance(value, str) and value:
                return value
        return "latest"

    @staticmethod
    def _normalize_usage(raw_usage: Any) -> dict[str, int | float]:
        """Keep only bounded numeric usage fields from a provider snapshot."""
        if not isinstance(raw_usage, Mapping):
            return {}
        usage: dict[str, int | float] = {}
        for key in (
            "seconds",
            "input_tokens",
            "output_tokens",
            "total_tokens",
            "cached_tokens",
            "reasoning_tokens",
            "input_audio_tokens",
            "output_audio_tokens",
        ):
            value = raw_usage.get(key)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                continue
            if (
                not math.isfinite(float(value))
                or value < 0
                or value > MAX_SAFE_USAGE_VALUE
            ):
                continue
            usage[key] = float(value) if isinstance(value, float) else value

        for details_key, audio_key in (
            ("input_token_details", "input_audio_tokens"),
            ("output_token_details", "output_audio_tokens"),
        ):
            details = raw_usage.get(details_key)
            if not isinstance(details, Mapping):
                continue
            for source_key, target_key in (
                ("audio_tokens", audio_key),
                ("cached_tokens", "cached_tokens"),
                ("reasoning_tokens", "reasoning_tokens"),
            ):
                value = details.get(source_key)
                if (
                    isinstance(value, (int, float))
                    and not isinstance(value, bool)
                    and math.isfinite(float(value))
                    and 0 <= value <= MAX_SAFE_USAGE_VALUE
                ):
                    usage[target_key] = int(value) if isinstance(value, int) else value
        return usage

    async def _record_usage(
        self,
        raw_usage: Any,
        *,
        source: str,
        identity: str = "latest",
    ) -> None:
        """Retain cumulative usage and emit only safe snapshot deltas."""
        snapshot = self._normalize_usage(raw_usage)
        if not snapshot:
            return

        if source == "live":
            previous = self._usage_snapshots["live"]
            self._usage_snapshots["live"] = dict(snapshot)
        else:
            previous = self._response_usage_snapshots.get(identity, {})
            self._response_usage_snapshots[identity] = dict(snapshot)
            self._usage_snapshots["responses"] = dict(snapshot)

        delta: dict[str, int | float] = {}
        for key, value in snapshot.items():
            old_value = previous.get(key, 0)
            if isinstance(value, (int, float)) and isinstance(old_value, (int, float)):
                difference = value - old_value
                if difference > 0:
                    delta[key] = difference

        seconds = delta.get("seconds")
        if isinstance(seconds, (int, float)) and seconds > 0:
            record(
                "platform.ai.audio.seconds",
                float(seconds),
                kind="histogram",
                provider="openai",
                stage="llm",
            )
            event("ai.usage", provider="openai", audio_seconds=float(seconds))

        token_keys = {
            "input_tokens",
            "output_tokens",
            "total_tokens",
            "cached_tokens",
            "reasoning_tokens",
            "input_audio_tokens",
            "output_audio_tokens",
        }
        if not token_keys.intersection(delta):
            return
        input_tokens = int(delta.get("input_tokens", 0))
        output_tokens = int(delta.get("output_tokens", 0))
        total_tokens = int(delta.get("total_tokens", input_tokens + output_tokens))
        await self.start_llm_usage_metrics(
            LLMTokenUsage(
                prompt_tokens=input_tokens,
                completion_tokens=output_tokens,
                total_tokens=total_tokens,
                cache_read_input_tokens=(
                    int(delta["cached_tokens"]) if "cached_tokens" in delta else None
                ),
                reasoning_tokens=(
                    int(delta["reasoning_tokens"])
                    if "reasoning_tokens" in delta
                    else None
                ),
                input_audio_tokens=(
                    int(delta["input_audio_tokens"])
                    if "input_audio_tokens" in delta
                    else None
                ),
                output_audio_tokens=(
                    int(delta["output_audio_tokens"])
                    if "output_audio_tokens" in delta
                    else None
                ),
            )
        )

    async def _handle_audio_delta(self, encoded_audio: Any) -> None:
        """Decode and resample provider PCM before emitting Pipecat audio."""
        if not isinstance(encoded_audio, str):
            await self._report_error("invalid_audio_delta", fatal=True)
            return
        try:
            audio = base64.b64decode(encoded_audio, validate=True)
            audio = audio[: len(audio) - (len(audio) % 2)]
            if not audio:
                return
            audio = await self._output_resampler.resample(
                audio,
                OPENAI_LIVE_AUDIO_RATE,
                self._output_sample_rate,
            )
        except (ValueError, TypeError):
            await self._report_error("invalid_audio_delta", fatal=True)
            return
        if not audio:
            return
        await self._begin_response_handoff()
        await self.push_frame(
            TTSAudioRawFrame(
                audio=audio,
                sample_rate=self._output_sample_rate,
                num_channels=1,
            )
        )

    async def _handle_output_text(self, text: Any) -> None:
        """Expose provider transcript text for UI telemetry and context."""
        if not isinstance(text, str) or not text:
            return
        await self._begin_response_handoff()
        llm_frame = LLMTextFrame(text)
        llm_frame.append_to_context = False
        tts_frame = TTSTextFrame(text, AggregationType.SENTENCE)
        tts_frame.append_to_context = False
        tts_frame.includes_inter_frame_spaces = True
        await self.push_frame(llm_frame)
        await self.push_frame(tts_frame)

    async def _handle_input_text(
        self,
        text: Any,
    ) -> None:
        """Accumulate ordered Live input transcript fragments for the next handoff."""
        if not isinstance(text, str) or not text:
            return
        if self._response_started:
            self._response_started = False
        self._input_transcript_fragments.append(text)

    async def _begin_response_handoff(self) -> None:
        """Finalize the current Live transcript before the assistant turn starts."""
        if self._response_started:
            return
        self._response_started = True
        transcript = "".join(self._input_transcript_fragments)
        self._input_transcript_fragments.clear()
        if transcript:
            await self.push_frame(
                TranscriptionFrame(
                    text=transcript,
                    user_id="",
                    timestamp=time_now_iso8601(),
                    finalized=True,
                ),
                direction=FrameDirection.UPSTREAM,
            )
        await self.push_frame(LLMFullResponseStartFrame())

    async def _handle_function_call(self, item: dict[str, Any]) -> None:
        """Execute one completed delegated function and resume Responses once."""
        call_id = item.get("call_id")
        name = item.get("name")
        arguments = item.get("arguments", {})
        if not isinstance(call_id, str) or not call_id:
            await self._report_error("function_call_missing_id", fatal=False)
            return
        if call_id in self._seen_tool_calls:
            await self._report_error("duplicate_function_call", fatal=False)
            return
        self._seen_tool_calls.add(call_id)
        if not isinstance(name, str) or not name:
            await self._submit_tool_result(call_id, {"error": "Tool name missing."})
            return
        try:
            if isinstance(arguments, str):
                arguments = json.loads(arguments)
            if not isinstance(arguments, Mapping):
                raise ValueError("arguments must be an object")
        except (TypeError, ValueError, json.JSONDecodeError):
            await self._submit_tool_result(
                call_id, {"error": "Tool arguments were not a valid JSON object."}
            )
            return

        if name not in self._functions and None not in self._functions:
            await self._submit_tool_result(
                call_id, {"error": "The requested tool is not available."}
            )
            return

        context = self._context or (
            LLMContext(tools=self._tools) if self._tools else LLMContext()
        )
        waiter = asyncio.Event()
        self._tool_result_events[call_id] = waiter
        try:
            await self.run_function_calls(
                [
                    FunctionCallFromLLM(
                        function_name=name,
                        tool_call_id=call_id,
                        arguments=dict(arguments),
                        context=context,
                    )
                ]
            )
            try:
                await asyncio.wait_for(waiter.wait(), timeout=self._tool_timeout)
                result = self._tool_results.get(call_id)
            except asyncio.TimeoutError:
                result = {"error": "Tool did not return a result in time."}
            if result is None:
                result = {"error": "Tool did not return a result."}
            await self._submit_tool_result(call_id, result)
        finally:
            self._tool_result_events.pop(call_id, None)
            self._tool_results.pop(call_id, None)

    async def _submit_tool_result(self, call_id: str, result: Any) -> None:
        """Submit one verified tool result and then continue delegated work."""
        if call_id in self._submitted_tool_calls:
            return
        self._submitted_tool_calls.add(call_id)
        if not isinstance(result, str):
            result = json.dumps(result, default=str)
        await self._send(
            {
                "type": "response.item.create",
                "event_id": self._event_id(),
                "item": {
                    "type": "function_call_output",
                    "call_id": call_id,
                    "output": result,
                },
            }
        )
        await self._send({"type": "response.create", "event_id": self._event_id()})

    async def _send_input_audio(self, frame: InputAudioRawFrame) -> None:
        """Resample input to mono PCM16 24 kHz and append it to Live."""
        audio = frame.audio[: len(frame.audio) - (len(frame.audio) % 2)]
        if not audio:
            return
        audio = await self._input_resampler.resample(
            audio,
            frame.sample_rate,
            OPENAI_LIVE_AUDIO_RATE,
        )
        audio = audio[: len(audio) - (len(audio) % 2)]
        if audio:
            await self._send(
                {
                    "type": "session.input_audio.append",
                    "audio": base64.b64encode(audio).decode("ascii"),
                }
            )

    async def _append_context(self, event_type: str, content: str) -> None:
        """Append session context and wait for its matching provider ack."""
        event_id = self._event_id()
        waiter = asyncio.get_running_loop().create_future()
        self._ack_waiters[event_id] = waiter
        try:
            await self._send(
                {
                    "type": event_type,
                    "event_id": event_id,
                    "delegation_id": None,
                    "content": content,
                }
            )
            await asyncio.wait_for(waiter, timeout=self._command_timeout)
        finally:
            self._ack_waiters.pop(event_id, None)

    def _resolve_ack(self, event: dict[str, Any]) -> None:
        """Resolve a command waiter from the provider's client event id."""
        client_event_id = event.get("client_event_id")
        if not isinstance(client_event_id, str):
            error = event.get("error")
            if isinstance(error, dict):
                client_event_id = error.get("client_event_id")
        if not isinstance(client_event_id, str):
            return
        waiter = self._ack_waiters.get(client_event_id)
        if waiter is not None and not waiter.done():
            if event.get("type") == "error":
                waiter.set_exception(OpenAILiveError("OpenAI Live command rejected."))
            else:
                waiter.set_result(event)

    async def _send(
        self,
        event: dict[str, Any],
        *,
        allow_before_start: bool = False,
    ) -> None:
        """Send one JSON command without exposing its body in logs."""
        if self._websocket is None:
            raise OpenAILiveError("OpenAI Live socket is not connected.")
        if not allow_before_start and (
            not self._session_ready
            or self._closed.is_set()
            or self._fatal_error is not None
        ):
            raise OpenAILiveError("OpenAI Live session is not ready.")
        async with self._send_lock:
            await self._websocket.send(json.dumps(event, separators=(",", ":")))

    async def _wait_until_started(self) -> None:
        """Wait for startup or return a safe connection error."""
        await asyncio.wait_for(self._started.wait(), timeout=self._connection_timeout)
        if self._fatal_error:
            raise self._fatal_error
        if not self._session_ready:
            await self._report_error("connection_closed", fatal=True)
            raise self._fatal_error or OpenAILiveError(
                "OpenAI Live session did not become ready.",
                code="connection_closed",
            )

    async def _report_error(self, code: str, *, fatal: bool) -> None:
        """Publish a safe error frame and retain only a non-sensitive code."""
        if fatal and self._fatal_error is None:
            self._fatal_error = OpenAILiveError(
                f"OpenAI Live error: {code}.",
                code=code,
            )
        if fatal:
            self._started.set()
        with suppress(Exception):
            await self.push_error(
                error_msg="OpenAI Live session failed.",
                exception=OpenAILiveError(
                    f"OpenAI Live error: {code}.",
                    code=code,
                ),
                fatal=fatal,
            )
        logger.error("OpenAI Live session error code=%s", code)

    async def _disconnect(self) -> None:
        """Request provider finalization, then close the socket and task."""
        websocket = self._websocket
        if websocket is None:
            return
        self._closing = True
        if self._session_ready and not self._closed.is_set():
            try:
                await self._send(
                    {"type": "session.close", "event_id": self._event_id()},
                    allow_before_start=True,
                )
            except Exception:  # noqa: BLE001 - preserve finalization failure safely
                await self._report_error("session_finalization_unconfirmed", fatal=True)
            if not self._closed.is_set():
                try:
                    await asyncio.wait_for(
                        self._closed.wait(), timeout=self._close_timeout
                    )
                except asyncio.TimeoutError:
                    await self._report_error(
                        "session_finalization_unconfirmed", fatal=True
                    )

        try:
            await websocket.close()
        except Exception:  # noqa: BLE001 - transport cleanup must continue
            if self._session_ready and not self._closed.is_set():
                await self._report_error("session_finalization_unconfirmed", fatal=True)
        if (
            self._receive_task is not None
            and self._receive_task is not asyncio.current_task()
        ):
            self._receive_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._receive_task
        self._receive_task = None
        self._websocket = None

    @staticmethod
    def _event_id() -> str:
        """Return a unique provider command id."""
        return f"event_{uuid.uuid4().hex}"


__all__ = ["OPENAI_LIVE_URL", "OpenAILiveError", "OpenAILiveLLMService"]
