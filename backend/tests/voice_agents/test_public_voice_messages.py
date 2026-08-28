"""Tests for safe public voice-session error messages."""

from src.voice_agents.public_voice_messages import get_public_voice_session_error


def test_insufficient_credit_error_is_safe_for_public_callers() -> None:
    """Do not expose organization billing details to visitors."""
    code, message = get_public_voice_session_error("INSUFFICIENT_CREDITS")

    assert code == "VOICE_ASSISTANT_UNAVAILABLE"
    assert "contact the business" in message.lower()
    assert "credits" not in message.lower()


def test_concurrent_limit_error_explains_retry_window() -> None:
    """Explain a temporary busy state without exposing plan configuration."""
    code, message = get_public_voice_session_error("MAX_CONCURRENT_CALLS")

    assert code == "VOICE_ASSISTANT_BUSY"
    assert "try again" in message.lower()


def test_demo_trial_exhaustion_is_explicit_and_safe() -> None:
    code, message = get_public_voice_session_error("DEMO_CALL_LIMIT_REACHED")

    assert code == "DEMO_TRIAL_EXHAUSTED"
    assert "trial calls" in message.lower()
    assert "contact the platform administrator" in message.lower()
    assert "re-enabled" in message.lower()
    assert "try again later" not in message.lower()
    assert "credits" not in message.lower()
