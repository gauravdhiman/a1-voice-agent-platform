"""Safe classification of voice-pipeline failures for call-log visibility."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class CallFailure:
    """A stable, non-sensitive failure marker persisted on a call log."""

    code: str
    message: str


class CallFailureState:
    """Keep the first pipeline failure observed during a voice session."""

    def __init__(self) -> None:
        self._failure: Optional[CallFailure] = None

    @property
    def failure(self) -> Optional[CallFailure]:
        """Return the first captured failure, if any."""
        return self._failure

    def capture(self, failure: CallFailure) -> None:
        """Capture only the first failure so the root cause remains visible."""
        if self._failure is None:
            self._failure = failure


def classify_pipeline_failure(error: object) -> CallFailure:
    """Map a provider/runtime error to a stable safe call-log classification.

    The raw error is used only in memory for classification. It is deliberately
    not returned or persisted because provider messages can contain request
    details, user content, or credential-adjacent diagnostics.
    """
    text = _error_text(error).lower()

    if (
        "reasoning" in text
        and any(term in text for term in ("mandatory", "required"))
        and any(term in text for term in ("disable", "none", "cannot"))
    ):
        return CallFailure(
            code="model_reasoning_required",
            message=(
                "The selected language model rejected the configured reasoning "
                "settings. Review the voice preset's model and reasoning "
                "configuration."
            ),
        )

    if any(
        marker in text
        for marker in (
            "401",
            "403",
            "unauthorized",
            "authentication",
            "invalid api key",
            "incorrect api key",
        )
    ):
        return CallFailure(
            code="provider_authentication_error",
            message=(
                "The speech provider rejected its credentials. Verify the "
                "provider API key for this agent."
            ),
        )

    if any(
        marker in text
        for marker in ("429", "rate limit", "rate_limit", "too many requests")
    ):
        return CallFailure(
            code="provider_rate_limited",
            message=(
                "The speech provider rate-limited this call. Try again or "
                "review the provider limits."
            ),
        )

    if any(
        marker in text
        for marker in (
            "502",
            "503",
            "504",
            "timeout",
            "timed out",
            "connection",
            "network",
            "temporarily unavailable",
            "service unavailable",
        )
    ):
        return CallFailure(
            code="provider_unavailable",
            message=(
                "The speech provider was unavailable during this call. Try "
                "again and check the provider status."
            ),
        )

    if "api key" in text and any(
        marker in text for marker in ("missing", "required", "not configured")
    ):
        return CallFailure(
            code="provider_configuration_error",
            message=(
                "A required speech-provider credential is not configured for "
                "this agent."
            ),
        )

    return CallFailure(
        code="voice_pipeline_error",
        message=(
            "The voice pipeline encountered an error. Review the provider "
            "configuration and runtime logs."
        ),
    )


def _error_text(error: object) -> str:
    """Collect error-frame and exception text without assuming a frame type."""
    values: list[str] = []
    for attribute in ("error", "exception"):
        value = getattr(error, attribute, None)
        if value is not None:
            values.append(str(value))
    if not values:
        values.append(str(error))
    return " ".join(values)


__all__ = ["CallFailure", "CallFailureState", "classify_pipeline_failure"]
