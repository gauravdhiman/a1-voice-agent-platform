"""Policy helpers for deciding whether a voice call may be recorded."""

from __future__ import annotations

from typing import Protocol


class AgentRecordingPreference(Protocol):
    """Minimum agent shape needed by the recording policy."""

    call_recording_enabled: bool


def should_record_agent_call(
    agent: AgentRecordingPreference,
    *,
    global_enabled: bool,
    tee_enabled: bool,
) -> bool:
    """Return whether recording is allowed for one agent's call.

    An agent must explicitly opt in before either the normal runtime gate or
    the development tee can start recording. This keeps the per-agent choice
    authoritative while preserving the existing environment-level safety
    switch for staged rollouts.

    Args:
        agent: Agent configuration containing the opt-in preference.
        global_enabled: Runtime feature flag for persisted recordings.
        tee_enabled: Development override for recording tee sessions.

    Returns:
        ``True`` only when the agent opted in and one runtime gate is enabled.
    """
    return bool(agent.call_recording_enabled) and (global_enabled or tee_enabled)
