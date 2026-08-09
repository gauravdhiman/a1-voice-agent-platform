"""Tests for safe public voice-session error messages."""

from src.voice_agents.public_voice_messages import (
    get_public_voice_session_error,
)


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
