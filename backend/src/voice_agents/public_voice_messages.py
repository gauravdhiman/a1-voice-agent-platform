"""Safe user-facing messages for unauthenticated voice call surfaces."""

from __future__ import annotations

PUBLIC_VOICE_ASSISTANT_UNAVAILABLE_MESSAGE = (
    "This voice assistant is temporarily unavailable. Please try again later "
    "or contact the business for assistance."
)
PUBLIC_VOICE_ASSISTANT_BUSY_MESSAGE = (
    "This voice assistant is currently busy helping other callers. Please try "
    "again in a few minutes or contact the business for assistance."
)


def get_public_voice_session_error(code: str) -> tuple[str, str]:
    """Translate an internal entitlement code into safe public guidance.

    Args:
        code: Internal voice-session denial code, such as
            ``INSUFFICIENT_CREDITS`` or ``MAX_CONCURRENT_CALLS``.

    Returns:
        A tuple of ``(public_code, message)`` suitable for a public API response
        or a spoken TwiML message. Internal plan and credit details are omitted.
    """
    if code == "MAX_CONCURRENT_CALLS":
        return "VOICE_ASSISTANT_BUSY", PUBLIC_VOICE_ASSISTANT_BUSY_MESSAGE
    return "VOICE_ASSISTANT_UNAVAILABLE", PUBLIC_VOICE_ASSISTANT_UNAVAILABLE_MESSAGE
