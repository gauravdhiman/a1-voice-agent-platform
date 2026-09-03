"""Owner-visible callback escalation storage (service-role only)."""

from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from opentelemetry import trace
from src.escalations.models import Escalation, EscalationCreate

from shared.organization.service import BaseOrganizationService

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

_COLUMNS = (
    "id,organization_id,agent_id,session_id,caller_phone,caller_name,"
    "reason,urgency,status,notified,created_at,acknowledged_at"
)


class EscalationService(BaseOrganizationService):
    """Persist and list callback escalations through the service-role client."""

    @tracer.start_as_current_span("escalations.create_escalation")
    async def create_escalation(
        self, organization_id: UUID, payload: EscalationCreate
    ) -> tuple[Optional[Escalation], Optional[str]]:
        """Manually log one callback request for an organization.

        Args:
            organization_id: Owning organization (from path, never client trust).
            payload: Validated callback details.

        Returns:
            Tuple of (escalation, error).
        """
        row = payload.model_dump(mode="json", exclude_none=True)
        row["organization_id"] = str(organization_id)
        row["status"] = "new"
        row["notified"] = False
        try:
            response = self.supabase.table("callback_escalations").insert(row).execute()
        except Exception:
            logger.error("Callback escalation insert failed", exc_info=True)
            return None, "Could not record the callback request."
        rows = getattr(response, "data", None) or []
        if not rows:
            return None, "Could not record the callback request."
        return Escalation(**rows[0]), None

    @tracer.start_as_current_span("escalations.list_escalations")
    async def list_escalations(
        self, organization_id: UUID, *, status: Optional[str] = None, limit: int = 100
    ) -> tuple[list[Escalation], Optional[str]]:
        """List escalations newest-first for one organization.

        Args:
            organization_id: Owning organization (from path).
            status: Optional follow-up status filter.
            limit: Maximum rows (1-200).

        Returns:
            Tuple of (escalations, error).
        """
        try:
            query = (
                self.supabase.table("callback_escalations")
                .select(_COLUMNS)
                .eq("organization_id", str(organization_id))
                .order("created_at", desc=True)
                .limit(max(1, min(limit, 200)))
            )
            if status:
                query = query.eq("status", status)
            response = query.execute()
        except Exception:
            logger.error("Callback escalation listing failed", exc_info=True)
            return [], "Could not load callback requests."
        rows = getattr(response, "data", None) or []
        return [Escalation(**row) for row in rows], None

    @tracer.start_as_current_span("escalations.mark_escalation_status")
    async def mark_status(
        self, organization_id: UUID, escalation_id: UUID, status: str
    ) -> tuple[Optional[Escalation], Optional[str]]:
        """Advance one escalation's follow-up status within its organization.

        Args:
            organization_id: Owning organization (row is matched on both id
                and organization to prevent cross-tenant updates).
            escalation_id: Escalation row id.
            status: One of new/acknowledged/resolved.

        Returns:
            Tuple of (updated escalation, error).
        """
        try:
            response = (
                self.supabase.table("callback_escalations")
                .update({"status": status})
                .eq("id", str(escalation_id))
                .eq("organization_id", str(organization_id))
                .execute()
            )
        except Exception:
            logger.error("Callback escalation status update failed", exc_info=True)
            return None, "Could not update the callback request."
        rows = getattr(response, "data", None) or []
        if not rows:
            return None, "Callback request not found."
        return Escalation(**rows[0]), None


escalation_service = EscalationService()
