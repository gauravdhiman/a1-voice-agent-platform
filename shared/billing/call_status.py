"""Shared constants for voice call lifecycle tracking."""

# Statuses that count toward ``max_concurrent_calls`` entitlement enforcement.
ACTIVE_VOICE_CALL_STATUSES: frozenset[str] = frozenset(
    {"initiated", "ringing", "answered"}
)
