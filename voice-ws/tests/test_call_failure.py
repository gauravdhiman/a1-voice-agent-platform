"""Tests for safe runtime failure classification."""

import pytest
from src.call_failure import CallFailureState, classify_pipeline_failure


@pytest.mark.parametrize(
    ("error", "code"),
    [
        (
            "Reasoning is mandatory for this endpoint and cannot be disabled",
            "model_reasoning_required",
        ),
        ("provider returned HTTP 401 Unauthorized", "provider_authentication_error"),
        ("provider returned HTTP 429 rate limit exceeded", "provider_rate_limited"),
        ("provider request timed out", "provider_unavailable"),
        (
            "Fish Audio server error during synthesis",
            "tts_empty_audio",
        ),
        (
            "Unknown error occurred: TTS returned empty audio",
            "tts_empty_audio",
        ),
        (
            "Unknown error occurred: 401 Unauthorized from Fish Audio",
            "provider_authentication_error",
        ),
    ],
)
def test_classify_pipeline_failure_returns_stable_codes(error, code):
    """Known provider failures are actionable without persisting raw details."""
    failure = classify_pipeline_failure(error)

    assert failure.code == code
    assert "Reasoning" not in failure.message
    assert "mandatory" not in failure.message
    assert len(failure.message) < 1000


def test_failure_state_keeps_first_root_cause():
    """Later cascading errors do not replace the first useful classification."""
    state = CallFailureState()
    first = classify_pipeline_failure("Reasoning is mandatory and cannot be disabled")
    second = classify_pipeline_failure("provider returned HTTP 503")

    state.capture(first)
    state.capture(second)

    assert state.failure == first
