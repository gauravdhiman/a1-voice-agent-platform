"""Tests for the per-agent call recording policy."""

from types import SimpleNamespace

from src.recording_policy import should_record_agent_call


def test_recording_requires_the_agent_setting_even_when_globally_enabled():
    """The global switch must not record agents that opted out."""
    agent = SimpleNamespace(call_recording_enabled=False)

    assert should_record_agent_call(agent, global_enabled=True, tee_enabled=False) is False


def test_recording_stays_off_when_both_switches_are_disabled():
    """An opted-in agent still needs a runtime recording gate."""
    agent = SimpleNamespace(call_recording_enabled=True)

    assert should_record_agent_call(agent, global_enabled=False, tee_enabled=False) is False


def test_recording_starts_for_an_opted_in_agent_when_globally_enabled():
    """An opted-in agent records when the environment allows recording."""
    agent = SimpleNamespace(call_recording_enabled=True)

    assert should_record_agent_call(agent, global_enabled=True, tee_enabled=False) is True


def test_recording_tee_can_enable_recording_for_an_opted_in_agent():
    """The development tee remains available, but only after agent opt-in."""
    agent = SimpleNamespace(call_recording_enabled=True)

    assert should_record_agent_call(agent, global_enabled=False, tee_enabled=True) is True
