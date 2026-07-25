"""Gemini realtime model configuration for the voice worker.

This module centralizes the kwargs passed to
``livekit.plugins.google.realtime.RealtimeModel`` so the conversation tuning —
which determines latency, tool-calling reliability, turn detection and barge-in
— is built in one place and is unit-testable without standing up a live
session or hitting the network.

The tuning decisions here fix the choppy, delayed, repetitive voice experience
documented in the model-options analysis. The four levers, in order of impact:

1. **Thinking disabled** (``thinking_budget=0``). On the Gemini-API native-audio
   model, thinking defaults ON, which causes 6+ second response latency *and*
   is the documented driver of the native-audio model's ~95-98% function-calling
   failure rate. Disabling it is the single biggest lever: it cuts latency and
   restores reliable tool calling at the same time. (The Vertex AI variant ships
   with thinking OFF for exactly this reason; we get the same benefit on the
   Gemini-API model by setting it explicitly.)

2. **Barge-in explicitly enabled** (``activity_handling=START_OF_ACTIVITY_INTERRUPTS``)
   so the agent stops and listens when the user speaks over it, instead of
   barreling ahead and repeating itself after the user already responded. This
   is the Gemini server default, but we set it explicitly so a future plugin
   change to the default cannot silently regress interruption.

3. **Endpointing tuned** (``silence_duration_ms=500``, ``prefix_padding_ms=200``)
   so the model commits end-of-turn faster after the user pauses, cutting the
   dead-air delay before the agent replies. Server-side automatic activity
   detection stays ON (``disabled`` is left unset) — the Gemini server does the
   VAD/endpointing, which is the correct layer for a native-audio realtime model.

4. **Temperature lowered** (0.8 -> 0.7) to reduce rambling and repetition.

The model is intentionally kept as the 2.5 native-audio preview. The newer
``gemini-3.1-flash-live-preview`` is NOT used because (a) the installed LiveKit
plugin does not support it (the support PR was closed, not merged), (b) it
forces *synchronous* function calling that blocks the conversation during every
tool call — directly conflicting with the low-latency requirement — and (c) it
breaks mid-session instruction / chat-context updates. See the model-options
analysis for the full rationale.

Tool-call behavior (``tool_behavior`` / ``tool_response_scheduling``) is left at
the Gemini defaults (BLOCKING / WHEN_IDLE). For a booking agent this is the
correct choice for *correctness*: the agent must wait for the
``check_availability`` / ``create_event`` result before telling the caller
whether a slot is open or the booking succeeded. NON_BLOCKING would let the
agent keep talking before it knows the result.
"""

from typing import Any

from google.genai import types
from livekit.plugins.google.realtime import RealtimeModel

# The model id. Kept as a module constant so the test suite (and any future
# operator) can reference / assert on it without a magic string in two places.
# Do NOT change this to the 3.1 "live" preview without re-reading the rationale
# in this module's docstring — the LiveKit plugin does not support it.
GEMINI_REALTIME_MODEL = "gemini-2.5-flash-native-audio-preview-12-2025"

# Endpointing tuning. ``silence_duration_ms`` is how much trailing silence the
# server requires before committing end-of-turn; lowering it cuts reply delay
# (too low → false endpoints that cut the user off mid-thought; 500ms is a
# snappy-but-safe middle). ``prefix_padding_ms`` is how much pre-speech audio is
# kept so a short utterance is not clipped at the start.
ENDPOINTING_SILENCE_DURATION_MS = 500
ENDPOINTING_PREFIX_PADDING_MS = 200

# Temperature lowered from the prior 0.8 to reduce rambling and repetition.
GEMINI_TEMPERATURE = 0.7
GEMINI_VOICE = "Puck"


def build_realtime_model_config() -> dict[str, Any]:
    """Build the kwargs for the Gemini RealtimeModel.

    Returns the tuning kwargs (everything except ``api_key``, which is supplied
    per-agent by :func:`build_realtime_model`). Returning a plain dict keeps this
    fully deterministic and unit-testable — the values can be asserted on without
    constructing a live model or opening a network connection.

    Returns:
        dict: kwargs accepted by ``RealtimeModel``. ``api_key`` is deliberately
        NOT included (it is agent-specific; supplied by ``build_realtime_model``).
    """
    return {
        "model": GEMINI_REALTIME_MODEL,
        "voice": GEMINI_VOICE,
        "temperature": GEMINI_TEMPERATURE,
        # Disable thinking. thinking_budget=0 is DISABLED (per Google's
        # ThinkingConfig contract: "0 is DISABLED. -1 is AUTOMATIC"). This cuts
        # response latency and fixes native-audio function-calling reliability.
        # include_thoughts=False keeps thoughts out of the transcript/audio.
        "thinking_config": types.ThinkingConfig(
            thinking_budget=0,
            include_thoughts=False,
        ),
        "realtime_input_config": types.RealtimeInputConfig(
            # Server-side VAD stays on (we do NOT set disabled=True) — the
            # Gemini server does endpointing for the native-audio model.
            automatic_activity_detection=types.AutomaticActivityDetection(
                silence_duration_ms=ENDPOINTING_SILENCE_DURATION_MS,
                prefix_padding_ms=ENDPOINTING_PREFIX_PADDING_MS,
            ),
            # Barge-in: user speech interrupts the agent's current response.
            # Explicit even though it is the Gemini default, so a plugin default
            # change cannot silently regress interruption.
            activity_handling=types.ActivityHandling.START_OF_ACTIVITY_INTERRUPTS,
        ),
    }


def build_realtime_model(api_key: str) -> RealtimeModel:
    """Construct the Gemini RealtimeModel with the tuned config.

    The model is constructed (opts stored) but no network connection is opened —
    the WebSocket is only opened when the LiveKit session starts the model. So
    this is safe to call in tests with a fake key.

    Args:
        api_key: The Gemini API key to use (per-agent: org key or platform key).

    Returns:
        RealtimeModel: the configured (but not yet connected) realtime model.
    """
    return RealtimeModel(api_key=api_key, **build_realtime_model_config())