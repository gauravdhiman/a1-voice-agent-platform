"""Google Gemini realtime (end-to-end speech) provider.

This module centralizes the kwargs passed to
``livekit.plugins.google.realtime.RealtimeModel`` so the conversation tuning —
which determines latency, tool-calling reliability, turn detection and
barge-in — is built in one place and is unit-testable without standing up a
live session or hitting the network.

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

Config-driven vs. fixed tuning:

- **User-tunable** (from :class:`RealtimeSpeechConfig`): model, voice,
  temperature, endpointing silence/prefix. These default to the constants below
  via :mod:`shared.voice_agents.speech_config`, so a config-less call reproduces
  today's behavior exactly.
- **Fixed** (not yet user-tunable): thinking disabled, barge-in enabled. These
  are the latency/reliability levers and are held constant here regardless of
  the config object.
"""

from typing import Any, Optional

from google.genai import types
from livekit.plugins.google.realtime import RealtimeModel

from shared.voice_agents.speech_config import (
    DEFAULT_ENDPOINTING_PREFIX_PADDING_MS,
    DEFAULT_ENDPOINTING_SILENCE_DURATION_MS,
    DEFAULT_REALTIME_MODEL,
    DEFAULT_REALTIME_TEMPERATURE,
    DEFAULT_REALTIME_VOICE,
    RealtimeSpeechConfig,
    default_realtime_config,
)

# ---------------------------------------------------------------------------
# Backward-compatible constant aliases.
#
# These mirror the constants that used to live in worker/src/realtime_config.py
# so any external importer (and the legacy test suite via the shim) keeps
# working. The single source of truth for the *defaults* is
# shared.voice_agents.speech_config; these aliases just re-export them under the
# old names. Do NOT change the model alias to the 3.1 "live" preview without
# re-reading the rationale in this module's docstring.
# ---------------------------------------------------------------------------
GEMINI_REALTIME_MODEL = DEFAULT_REALTIME_MODEL
GEMINI_TEMPERATURE = DEFAULT_REALTIME_TEMPERATURE
GEMINI_VOICE = DEFAULT_REALTIME_VOICE
ENDPOINTING_SILENCE_DURATION_MS = DEFAULT_ENDPOINTING_SILENCE_DURATION_MS
ENDPOINTING_PREFIX_PADDING_MS = DEFAULT_ENDPOINTING_PREFIX_PADDING_MS


def build_realtime_model_config(
    config: Optional[RealtimeSpeechConfig] = None,
) -> dict[str, Any]:
    """Build the kwargs for the Gemini RealtimeModel from a speech config.

    Args:
        config: The realtime speech config. If ``None``, the default realtime
            config is used (today's behavior — Google native-audio model, Puck
            voice, temperature 0.7, endpointing 500/200ms).

    Returns:
        dict: kwargs accepted by ``RealtimeModel``. ``api_key`` is deliberately
        NOT included (it is agent-specific; supplied by
        :func:`build_realtime_model`). Returning a plain dict keeps this fully
        deterministic and unit-testable — the values can be asserted on without
        constructing a live model or opening a network connection.

    Notes:
        - User-tunable knobs (model, voice, temperature, endpointing) come from
          ``config``.
        - Fixed tuning (thinking disabled, barge-in enabled) is set here
          regardless of ``config``.
    """
    cfg = config if config is not None else default_realtime_config()
    return {
        "model": cfg.model,
        "voice": cfg.voice,
        "temperature": cfg.temperature,
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
                silence_duration_ms=cfg.silence_duration_ms,
                prefix_padding_ms=cfg.prefix_padding_ms,
            ),
            # Barge-in: user speech interrupts the agent's current response.
            # Explicit even though it is the Gemini default, so a plugin default
            # change cannot silently regress interruption.
            activity_handling=types.ActivityHandling.START_OF_ACTIVITY_INTERRUPTS,
        ),
    }


def build_realtime_model(
    api_key: str,
    config: Optional[RealtimeSpeechConfig] = None,
) -> RealtimeModel:
    """Construct the Gemini RealtimeModel with the tuned config.

    The model is constructed (opts stored) but no network connection is opened —
    the WebSocket is only opened when the LiveKit session starts the model. So
    this is safe to call in tests with a fake key.

    Args:
        api_key: The Gemini API key to use (per-agent: org key or platform key).
        config: The realtime speech config. If ``None``, the default realtime
            config is used.

    Returns:
        RealtimeModel: the configured (but not yet connected) realtime model.
    """
    return RealtimeModel(api_key=api_key, **build_realtime_model_config(config))


__all__ = [
    "GEMINI_REALTIME_MODEL",
    "GEMINI_TEMPERATURE",
    "GEMINI_VOICE",
    "ENDPOINTING_SILENCE_DURATION_MS",
    "ENDPOINTING_PREFIX_PADDING_MS",
    "build_realtime_model_config",
    "build_realtime_model",
]
