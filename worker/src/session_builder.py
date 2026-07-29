"""Session builder — the single seam where realtime vs pipeline diverge.

Builds a LiveKit ``AgentSession`` from a
:class:`shared.voice_agents.speech_config.SpeechConfig` and a per-provider
API-key map. This is the *only* place the two engine modes diverge: everything
upstream (room dispatch, agent fetch, prompt build, tool/MCP wiring, key
resolution) and downstream (room join, greeting, cleanup) is shared and
engine-agnostic.

- **realtime** — ``AgentSession(llm=RealtimeModel, userdata=...)``. The single
  end-to-end model handles STT + LLM + TTS.
- **pipeline** — ``AgentSession(stt=..., llm=..., tts=..., vad=...,
  turn_detection=..., userdata=...)``. Each stage is an independently-configured
  LiveKit plugin. Wired in Phase 2.

The builder delegates plugin construction to
:func:`speech_providers.registry.build_session_components` and only decides how
to assemble the ``AgentSession`` from the resulting components. This keeps the
provider factory (swappable per-stage backends) separate from the session
assembly (LiveKit's ``AgentSession`` contract).
"""

from typing import Any, Union

from livekit.agents import AgentSession
from speech_providers.registry import (
    PipelineComponents,
    RealtimeComponents,
    build_session_components,
)

from shared.voice_agents.speech_config import PipelineSpeechConfig, RealtimeSpeechConfig


def build_agent_session(
    speech_config: Union[RealtimeSpeechConfig, PipelineSpeechConfig],
    api_keys: dict[str, str],
    userdata: dict[str, Any],
) -> AgentSession:
    """Build a LiveKit AgentSession for the given speech config.

    Args:
        speech_config: The agent's speech config (realtime or pipeline). For a
            realtime config, an ``AgentSession`` with the RealtimeModel as
            ``llm`` is returned. For a pipeline config, the session is assembled
            from the per-stage plugins (Phase 2).
        api_keys: Per-provider API key map forwarded to
            :func:`build_session_components`.
        userdata: Arbitrary data attached to the session (e.g.
            ``{"agent_id": ..., "agent_name": ...}``); retrievable via
            ``session.userdata`` and used by the agent's ``on_enter``.

    Returns:
        AgentSession: the constructed (not yet started) session. The caller
        starts it with ``session.start(room=..., agent=...)``.

    Raises:
        ValueError: If a required provider key is missing (propagated from
            :func:`build_session_components`).
        NotImplementedError: If a pipeline config is given (Phase 2 wires the
            pipeline session assembly).

    Example:
        ```python
        session = build_agent_session(
            speech_config=default_realtime_config(),
            api_keys={"google": api_key},
            userdata={"agent_id": agent_id, "agent_name": voice_agent.name},
        )
        await session.start(room=ctx.room, agent=livekit_agent, ...)
        ```
    """
    components = build_session_components(speech_config, api_keys)

    if isinstance(components, RealtimeComponents):
        # End-to-end: the single RealtimeModel is passed as llm=. No separate
        # stt/tts — the model handles both over the native-audio WebSocket.
        return AgentSession(llm=components.llm, userdata=userdata)

    if isinstance(components, PipelineComponents):
        # Phase 2: assemble the pipeline session from the per-stage plugins.
        # Raised now so a pipeline config can't silently degrade to realtime.
        raise NotImplementedError(
            "Pipeline engine session assembly is not implemented yet (Phase 2)."
        )

    # Defensive: the components union is closed, but guard against a future
    # variant so this fails loudly rather than returning an unconfigured session.
    raise TypeError(f"Unsupported session components type: {type(components).__name__}")


__all__ = ["build_agent_session"]
