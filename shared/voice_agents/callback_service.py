"""Owner-visible callback requests from soft escalation.

Production voice calls (never demos) record one row per accepted
``request_human_callback`` tool result through
:func:`record_callback_tool_outcome`, invoked by the voice runtime tool
adapter next to the demo-outcome hook. This is the explicit
workflow/orchestration boundary: the tool itself only validates arguments
and notifies the owner; persistence lives here, deterministically, with no
model involvement.

Demo sessions are skipped: the demo organization is shared and neutral,
and demo outcomes already have their receipt path.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from shared.config import supabase_config
from shared.voice_agents.tools.base.tool_context import ToolContext

logger = logging.getLogger(__name__)

CALLBACK_TOOL_FUNCTION = "request_human_callback"

#: Tool result statuses that produce a dashboard row.
_RECORDABLE_STATUSES = frozenset({"notified", "accepted"})

_COLUMNS = (
    "id,organization_id,agent_id,session_id,caller_phone,caller_name,"
    "reason,urgency,status,notified,created_at,acknowledged_at"
)


def _response_rows(response: Any) -> list[dict[str, Any]]:
    """Return row dicts from a Supabase response, tolerating fakes."""
    data = getattr(response, "data", None) or []
    return [row for row in data if isinstance(row, dict)]


def _text(value: Any, *, limit: int) -> Optional[str]:
    """Bound free-form text for storage without leaking internals."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text[:limit]


class CallbackEscalationService:
    """Persist and read callback escalations through the service role."""

    def __init__(self, client: Any = None) -> None:
        """Create the service with an optional injected client (tests)."""
        self.client = client

    def _client(self) -> Any:
        """Return the injected or configured service-role client."""
        return self.client or supabase_config.service_client

    def _insert_sync(self, row: dict[str, Any]) -> Optional[dict[str, Any]]:
        """Insert one escalation row; None when storage is unavailable."""
        client = self._client()
        if client is None:
            raise RuntimeError("Callback escalation storage is not configured")
        response = client.table("callback_escalations").insert(row).execute()
        rows = _response_rows(response)
        return rows[0] if rows else None

    async def record(
        self,
        *,
        organization_id: str,
        agent_id: Optional[str],
        session_id: Optional[str],
        caller_phone: str,
        caller_name: Optional[str],
        reason: str,
        urgency: str,
        notified: bool,
    ) -> Optional[dict[str, Any]]:
        """Insert one escalation row for an accepted callback request."""
        row = {
            "organization_id": organization_id,
            "agent_id": agent_id,
            "session_id": session_id,
            "caller_phone": caller_phone,
            "caller_name": caller_name,
            "reason": reason,
            "urgency": urgency if urgency in ("normal", "urgent") else "normal",
            "status": "new",
            "notified": notified,
        }
        return await asyncio.to_thread(self._insert_sync, row)

    def _list_sync(
        self, *, organization_id: str, status: Optional[str], limit: int
    ) -> list[dict[str, Any]]:
        """List newest-first escalation rows for one organization."""
        client = self._client()
        if client is None:
            raise RuntimeError("Callback escalation storage is not configured")
        query = (
            client.table("callback_escalations")
            .select(_COLUMNS)
            .eq("organization_id", organization_id)
            .order("created_at", desc=True)
            .limit(max(1, min(limit, 200)))
        )
        if status:
            query = query.eq("status", status)
        return _response_rows(query.execute())

    async def list_for_organization(
        self, *, organization_id: str, status: Optional[str] = None, limit: int = 100
    ) -> list[dict[str, Any]]:
        """Return newest-first escalation rows for one organization."""
        return await asyncio.to_thread(
            self._list_sync,
            organization_id=organization_id,
            status=status,
            limit=limit,
        )


callback_escalation_service = CallbackEscalationService()


def _payload_from_tool_result(
    *,
    context: ToolContext,
    arguments: dict[str, Any],
    result: Any,
) -> Optional[dict[str, Any]]:
    """Build a storage row from an accepted callback tool result."""
    if not isinstance(result, dict):
        return None
    if str(result.get("status", "")).lower() not in _RECORDABLE_STATUSES:
        return None
    if not context.organization_id:
        return None
    caller_phone = _text(arguments.get("callback_phone"), limit=32) or _text(
        result.get("callback_phone"), limit=32
    )
    reason = _text(arguments.get("reason"), limit=500) or _text(
        result.get("reason"), limit=500
    )
    if not caller_phone or not reason:
        return None
    return {
        "organization_id": context.organization_id,
        "agent_id": context.agent_id,
        "session_id": context.session_id,
        "caller_phone": caller_phone,
        "caller_name": _text(arguments.get("caller_name"), limit=100),
        "reason": reason,
        "urgency": (
            str(arguments.get("urgency", "normal")).lower()
            if str(arguments.get("urgency", "")).lower() in ("normal", "urgent")
            else "normal"
        ),
        "notified": bool(result.get("notified", False)),
    }


async def record_callback_tool_outcome(
    *,
    context: Optional[ToolContext],
    function_name: str,
    arguments: dict[str, Any],
    result: Any,
) -> bool:
    """Persist an accepted ``request_human_callback`` result as an escalation.

    Mirrors ``record_demo_tool_outcome`` for production soft escalation.
    Returns True when a row was stored. Never raises: storage failures are
    logged (the owner email alert is the time-critical path and already
    went out from the tool itself).
    """
    if not context or context.is_demo:
        return False
    if function_name != CALLBACK_TOOL_FUNCTION:
        return False
    payload = _payload_from_tool_result(
        context=context, arguments=arguments, result=result
    )
    if payload is None:
        return False
    try:
        stored = await callback_escalation_service.record(
            organization_id=str(payload["organization_id"]),
            agent_id=payload["agent_id"],
            session_id=payload["session_id"],
            caller_phone=str(payload["caller_phone"]),
            caller_name=payload["caller_name"],
            reason=str(payload["reason"]),
            urgency=str(payload["urgency"]),
            notified=bool(payload["notified"]),
        )
    except Exception:
        logger.exception(
            "Callback escalation persistence failed session_id=%s",
            context.session_id,
        )
        return False
    if stored is None:
        logger.warning(
            "Callback escalation insert returned no row session_id=%s",
            context.session_id,
        )
        return False
    logged_at = datetime.now(timezone.utc).isoformat()
    logger.info(
        "Callback escalation recorded session_id=%s at=%s",
        context.session_id,
        logged_at,
    )
    return True


__all__ = [
    "CALLBACK_TOOL_FUNCTION",
    "CallbackEscalationService",
    "callback_escalation_service",
    "record_callback_tool_outcome",
]
