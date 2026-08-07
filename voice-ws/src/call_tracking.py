"""Track voice WebSocket sessions in ``call_logs`` for concurrent call limits."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from shared.config import supabase_config

logger = logging.getLogger(__name__)


async def start_call_tracking(
    *,
    session_id: str,
    organization_id: UUID,
    agent_id: UUID,
) -> Optional[str]:
    """Insert an active call log row for a voice session.

    Args:
        session_id: Voice session identifier (stored as ``call_sid``).
        organization_id: Owning organization UUID.
        agent_id: Voice agent UUID.

    Returns:
        Call log row id string, or None if tracking could not be persisted.
    """
    client = supabase_config.client
    if client is None:
        return None

    now = datetime.now(timezone.utc).isoformat()
    row = {
        "call_sid": session_id,
        "organization_id": str(organization_id),
        "agent_id": str(agent_id),
        "status": "initiated",
        "duration": 0,
        "started_at": now,
        "created_at": now,
        "updated_at": now,
    }
    try:
        result = client.table("call_logs").insert(row).execute()
        if result.data:
            return str(result.data[0]["id"])
    except Exception:
        logger.exception(
            "Failed to create call log for session_id=%s org=%s",
            session_id,
            organization_id,
        )
    return None


async def end_call_tracking(
    call_log_id: Optional[str],
    *,
    status: str = "completed",
) -> None:
    """Mark a tracked call log row as finished."""
    if not call_log_id:
        return
    client = supabase_config.client
    if client is None:
        return

    now = datetime.now(timezone.utc).isoformat()
    try:
        client.table("call_logs").update(
            {
                "status": status,
                "ended_at": now,
                "updated_at": now,
            }
        ).eq("id", call_log_id).execute()
    except Exception:
        logger.exception("Failed to finalize call log id=%s", call_log_id)
