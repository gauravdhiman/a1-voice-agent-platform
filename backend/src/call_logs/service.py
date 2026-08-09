"""Service layer for call log operations."""

import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from uuid import UUID

from shared.config import supabase_config

from .models import (
    CallAnalytics,
    CallLog,
    CallLogCreate,
    CallLogsResponse,
    CallLogUpdate,
)

logger = logging.getLogger(__name__)


class CallLogService:
    """Handles all call log CRUD and analytics operations."""

    @property
    def supabase(self):
        return supabase_config.client

    async def create_call_log(
        self, data: CallLogCreate
    ) -> Tuple[Optional[CallLog], Optional[str]]:
        """Insert a new call log record."""
        try:
            payload = {
                "call_sid": data.call_sid,
                "organization_id": str(data.organization_id),
                "agent_id": str(data.agent_id) if data.agent_id else None,
                "caller_number": data.caller_number,
                "called_number": data.called_number,
                "status": data.status,
                "duration": data.duration,
                "started_at": data.started_at.isoformat() if data.started_at else None,
                "ended_at": data.ended_at.isoformat() if data.ended_at else None,
            }
            result = self.supabase.table("call_logs").insert(payload).execute()
            if not result.data:
                return None, "Failed to create call log"
            return CallLog(**result.data[0]), None
        except Exception as e:
            logger.error(f"Error creating call log: {e}", exc_info=True)
            return None, str(e)

    async def update_call_log_by_sid(
        self, call_sid: str, data: CallLogUpdate
    ) -> Tuple[Optional[CallLog], Optional[str]]:
        """Update a call log by its Twilio CallSid."""
        try:
            payload = {k: v for k, v in data.model_dump().items() if v is not None}
            if "ended_at" in payload and isinstance(payload["ended_at"], datetime):
                payload["ended_at"] = payload["ended_at"].isoformat()
            payload["updated_at"] = datetime.now(timezone.utc).isoformat()

            result = (
                self.supabase.table("call_logs")
                .update(payload)
                .eq("call_sid", call_sid)
                .execute()
            )
            if not result.data:
                return None, "Call log not found"
            return CallLog(**result.data[0]), None
        except Exception as e:
            logger.error(f"Error updating call log: {e}", exc_info=True)
            return None, str(e)

    async def list_call_logs(
        self,
        organization_id: UUID,
        agent_id: Optional[UUID] = None,
        status: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 25,
    ) -> Tuple[Optional[CallLogsResponse], Optional[str]]:
        """List call logs with optional filters and pagination."""
        try:
            query = (
                self.supabase.table("call_logs")
                .select("*", count="exact")
                .eq("organization_id", str(organization_id))
                .order("created_at", desc=True)
            )

            if agent_id:
                query = query.eq("agent_id", str(agent_id))
            if status:
                query = query.eq("status", status)
            if date_from:
                query = query.gte("created_at", date_from.isoformat())
            if date_to:
                query = query.lte("created_at", date_to.isoformat())

            offset = (page - 1) * page_size
            query = query.range(offset, offset + page_size - 1)

            result = query.execute()
            total = result.count or 0
            rows = result.data or []
            recording_call_ids: set[str] = set()
            if rows:
                try:
                    artifact_result = (
                        self.supabase.table("call_artifacts")
                        .select("call_log_id")
                        .in_("call_log_id", [str(row["id"]) for row in rows])
                        .eq("artifact_type", "recording")
                        .eq("status", "completed")
                        .execute()
                    )
                    recording_call_ids = {
                        str(row["call_log_id"]) for row in (artifact_result.data or [])
                    }
                except Exception:  # noqa: BLE001 - old DBs may not have artifacts yet
                    logger.warning(
                        "Could not load recording availability; returning call logs",
                        exc_info=True,
                    )
            items = [
                CallLog(
                    **row,
                    recording_available=str(row["id"]) in recording_call_ids,
                )
                for row in rows
            ]
            total_pages = max(1, (total + page_size - 1) // page_size)

            return (
                CallLogsResponse(
                    items=items,
                    total=total,
                    page=page,
                    page_size=page_size,
                    total_pages=total_pages,
                ),
                None,
            )
        except Exception as e:
            logger.error(f"Error listing call logs: {e}", exc_info=True)
            return None, str(e)

    async def get_analytics(
        self, organization_id: UUID
    ) -> Tuple[Optional[CallAnalytics], Optional[str]]:
        """Compute call analytics for the given organization."""
        try:
            now = datetime.now(timezone.utc)
            week_ago = now - timedelta(days=7)
            month_ago = now - timedelta(days=30)

            # Fetch all calls in the last 30 days (sufficient for week + month stats)
            result = (
                self.supabase.table("call_logs")
                .select("*")
                .eq("organization_id", str(organization_id))
                .gte("created_at", month_ago.isoformat())
                .execute()
            )
            rows = result.data or []

            total_calls_week = 0
            total_calls_month = len(rows)
            total_duration = 0
            calls_by_agent: dict = defaultdict(
                lambda: {"count": 0, "agent_id": None, "agent_name": "Unknown"}
            )
            calls_by_hour: dict = defaultdict(int)
            calls_by_status: dict = defaultdict(int)

            for row in rows:
                created = datetime.fromisoformat(
                    row["created_at"].replace("Z", "+00:00")
                )
                if created >= week_ago:
                    total_calls_week += 1

                duration = row.get("duration") or 0
                total_duration += duration

                agent_id = row.get("agent_id") or "unknown"
                calls_by_agent[agent_id]["count"] += 1
                calls_by_agent[agent_id]["agent_id"] = agent_id

                hour = created.hour
                calls_by_hour[hour] += 1

                status = row.get("status", "unknown")
                calls_by_status[status] += 1

            avg_duration = (
                (total_duration / total_calls_month) if total_calls_month > 0 else 0.0
            )

            # Fetch agent names for the IDs we have
            agent_ids = [k for k in calls_by_agent if k != "unknown"]
            agent_names: dict = {}
            if agent_ids:
                agents_result = (
                    self.supabase.table("voice_agents")
                    .select("id, name")
                    .in_("id", agent_ids)
                    .execute()
                )
                agent_names = {a["id"]: a["name"] for a in (agents_result.data or [])}

            for agent_id, data in calls_by_agent.items():
                data["agent_name"] = agent_names.get(agent_id, "Unknown")

            # Build hour-by-hour list (0-23)
            hour_list = [
                {"hour": h, "calls": calls_by_hour.get(h, 0)} for h in range(24)
            ]
            status_list = [
                {"status": s, "count": c} for s, c in calls_by_status.items()
            ]
            agent_list = sorted(
                calls_by_agent.values(), key=lambda x: x["count"], reverse=True
            )

            return (
                CallAnalytics(
                    total_calls_week=total_calls_week,
                    total_calls_month=total_calls_month,
                    avg_duration_seconds=round(avg_duration, 1),
                    calls_by_agent=agent_list,
                    calls_by_hour=hour_list,
                    calls_by_status=status_list,
                ),
                None,
            )
        except Exception as e:
            logger.error(f"Error computing analytics: {e}", exc_info=True)
            return None, str(e)


call_log_service = CallLogService()
