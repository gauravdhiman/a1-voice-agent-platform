"""Private interest-lead storage (service-role only, no public DB policy)."""

from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from opentelemetry import trace
from src.leads.models import InterestLead, InterestLeadCreate

from shared.organization.service import BaseOrganizationService

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

_LEAD_COLUMNS = (
    "id,name,business_name,email,phone,vertical,message,"
    "source,demo_slug,status,created_at,contacted_at"
)


class LeadService(BaseOrganizationService):
    """Persist and list interest leads through the service-role client."""

    @tracer.start_as_current_span("leads.submit_interest_lead")
    async def submit_lead(
        self, payload: InterestLeadCreate
    ) -> tuple[Optional[InterestLead], Optional[str]]:
        """Insert one interest lead.

        Args:
            payload: Validated visitor submission.

        Returns:
            Tuple of (lead, error). ``error`` is a safe message; database
            internals are never surfaced to the public caller.
        """
        try:
            response = (
                self.supabase.table("interest_leads")
                .insert(
                    payload.model_dump(
                        mode="json",
                        exclude_none=True,
                        exclude={"captcha_token"},
                    )
                )
                .execute()
            )
        except Exception:
            logger.error("Interest lead insert failed", exc_info=True)
            return None, "Could not record your request. Please try again."
        rows = getattr(response, "data", None) or []
        if not rows:
            return None, "Could not record your request. Please try again."
        return InterestLead(**rows[0]), None

    @tracer.start_as_current_span("leads.get_interest_lead")
    async def get_lead(
        self, lead_id: UUID
    ) -> tuple[Optional[InterestLead], Optional[str]]:
        """Load one lead for an internal notification retry.

        Args:
            lead_id: The private interest-lead identifier.

        Returns:
            Tuple of (lead, error). The error is safe for internal callers and
            does not contain database details.
        """
        try:
            response = (
                self.supabase.table("interest_leads")
                .select(_LEAD_COLUMNS)
                .eq("id", str(lead_id))
                .single()
                .execute()
            )
        except Exception:
            logger.error("Interest lead lookup failed", exc_info=True)
            return None, "Could not load the interest lead."
        row = getattr(response, "data", None)
        if not row:
            return None, "Interest lead not found."
        return InterestLead(**row), None

    @tracer.start_as_current_span("leads.list_interest_leads")
    async def list_leads(
        self, *, status: Optional[str] = None, limit: int = 100
    ) -> tuple[list[InterestLead], Optional[str]]:
        """List leads newest-first for platform admins.

        Args:
            status: Optional status filter (new/contacted/invited/...).
            limit: Maximum rows (1-500).

        Returns:
            Tuple of (leads, error).
        """
        try:
            query = (
                self.supabase.table("interest_leads")
                .select(_LEAD_COLUMNS)
                .order("created_at", desc=True)
                .limit(max(1, min(limit, 500)))
            )
            if status:
                query = query.eq("status", status)
            response = query.execute()
        except Exception:
            logger.error("Interest lead listing failed", exc_info=True)
            return [], "Could not load interest leads."
        rows = getattr(response, "data", None) or []
        return [InterestLead(**row) for row in rows], None

    @tracer.start_as_current_span("leads.mark_lead_status")
    async def mark_status(
        self, lead_id: UUID, status: str
    ) -> tuple[Optional[InterestLead], Optional[str]]:
        """Advance one lead's follow-up status.

        Args:
            lead_id: Lead row id.
            status: One of new/contacted/invited/converted/dropped.

        Returns:
            Tuple of (updated lead, error).
        """
        try:
            response = (
                self.supabase.table("interest_leads")
                .update({"status": status})
                .eq("id", str(lead_id))
                .execute()
            )
        except Exception:
            logger.error("Interest lead status update failed", exc_info=True)
            return None, "Could not update the lead."
        rows = getattr(response, "data", None) or []
        if not rows:
            return None, "Lead not found."
        return InterestLead(**rows[0]), None


lead_service = LeadService()
