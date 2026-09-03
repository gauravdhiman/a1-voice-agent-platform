"""Transport-neutral runtime context injected into shared tool methods."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class ToolContext:
    """Trusted per-session metadata available to tool implementations.

    The model never supplies these values as function arguments.  The voice
    runtime resolves them from the authenticated agent and organization before
    assembling tools.  Provider-neutral tools can ignore fields they do not
    need; scheduling tools use the organization timezone and session id for
    datetime normalization and safe retry handling.

    Attributes:
        organization_id: Organization owning the active agent, when known.
        agent_id: Active voice-agent identifier, when known.
        organization_timezone: Valid IANA timezone for the organization's
            business calendar.  Defaults to UTC only as a last-resort runtime
            fallback.
        session_id: Stable voice session identifier used for operation-scoped
            idempotency where a provider supports it.
        is_demo: Whether the authenticated session belongs to a public demo
            agent.  Only demo-specific visitor receipts may use this flag.
        demo_slug: Public slug for the active demo agent, when applicable.
        current_time: Optional fixed execution time.  Production callers leave
            this unset so tools read the current clock; tests may set it.
    """

    organization_id: Optional[str] = None
    agent_id: Optional[str] = None
    organization_timezone: str = "UTC"
    session_id: Optional[str] = None
    is_demo: bool = False
    demo_slug: Optional[str] = None
    current_time: Optional[datetime] = None
