"""Service layer for call log operations."""

import asyncio
import logging
from collections import defaultdict
from datetime import datetime, time, timedelta, timezone
from typing import Literal, Optional, Tuple
from uuid import UUID
from zoneinfo import ZoneInfo

from opentelemetry import trace

from shared.config import supabase_config

from .models import (
    CallAnalytics,
    CallLog,
    CallLogCreate,
    CallLogsResponse,
    CallLogUpdate,
)

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)
UNASSIGNED_AGENT_KEY = "__unassigned__"


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
                "source_type": data.source_type,
                "source_url": data.source_url,
                "source_domain": data.source_domain,
                "status": data.status,
                "failure_code": data.failure_code,
                "failure_message": data.failure_message,
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

            # The Twilio status callback can arrive after voice-ws has already
            # classified a runtime failure. Apply completion updates only while
            # the failure marker is still null so the provider callback cannot
            # race with, or overwrite, the root-cause marker.
            if payload.get("status") in {"completed", "answered"}:
                result = (
                    self.supabase.table("call_logs")
                    .update(payload)
                    .eq("call_sid", call_sid)
                    .is_("failure_code", "null")
                    .execute()
                )
                if not result.data:
                    existing = (
                        self.supabase.table("call_logs")
                        .select("id,failure_code")
                        .eq("call_sid", call_sid)
                        .limit(1)
                        .execute()
                    )
                    if not existing.data:
                        return None, "Call log not found"

                    if existing.data[0].get("failure_code"):
                        # Keep timing/provider metadata from the late callback,
                        # but never replace the failure status or its marker.
                        preserved_payload = {
                            key: value
                            for key, value in payload.items()
                            if key not in {"status", "failure_code", "failure_message"}
                        }
                        result = (
                            self.supabase.table("call_logs")
                            .update(preserved_payload)
                            .eq("call_sid", call_sid)
                            .execute()
                        )
                    else:
                        # A response without rows is unusual, but retry the
                        # conditional mutation once for clients configured not
                        # to return updated rows by default.
                        result = (
                            self.supabase.table("call_logs")
                            .update(payload)
                            .eq("call_sid", call_sid)
                            .is_("failure_code", "null")
                            .execute()
                        )
                        if not result.data:
                            # A runtime failure may have won the race between
                            # the read above and this retry. Preserve it while
                            # still accepting the provider's timing metadata.
                            latest = (
                                self.supabase.table("call_logs")
                                .select("id,failure_code")
                                .eq("call_sid", call_sid)
                                .limit(1)
                                .execute()
                            )
                            if not latest.data:
                                return None, "Call log not found"
                            if latest.data[0].get("failure_code"):
                                preserved_payload = {
                                    key: value
                                    for key, value in payload.items()
                                    if key
                                    not in {
                                        "status",
                                        "failure_code",
                                        "failure_message",
                                    }
                                }
                                result = (
                                    self.supabase.table("call_logs")
                                    .update(preserved_payload)
                                    .eq("call_sid", call_sid)
                                    .execute()
                                )
            else:
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
        source_type: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        recording_only: bool = False,
        page: int = 1,
        page_size: int = 25,
        date_to_exclusive: Optional[datetime] = None,
    ) -> Tuple[Optional[CallLogsResponse], Optional[str]]:
        """List call logs with optional filters and pagination.

        When ``recording_only`` is enabled, only calls with a completed
        recording artifact are returned. The filter is applied before
        pagination so an agent's recordings tab does not hide recordings on
        later pages because unrecorded calls occupy the first page. Use
        ``date_to_exclusive`` for half-open reporting windows; ``date_to``
        remains inclusive for existing callers.
        """
        try:
            recording_call_ids: Optional[set[str]] = None
            if recording_only:
                try:
                    artifact_result = (
                        self.supabase.table("call_artifacts")
                        .select("call_log_id")
                        .eq("organization_id", str(organization_id))
                        .eq("artifact_type", "recording")
                        .eq("status", "completed")
                        .execute()
                    )
                    recording_call_ids = {
                        str(row["call_log_id"])
                        for row in (artifact_result.data or [])
                        if row.get("call_log_id")
                    }
                except Exception:  # noqa: BLE001 - old DBs may not have artifacts yet
                    logger.warning(
                        "Could not load recording-only call logs; returning no recordings",
                        exc_info=True,
                    )
                    recording_call_ids = set()

                if not recording_call_ids:
                    return (
                        CallLogsResponse(
                            items=[],
                            total=0,
                            page=page,
                            page_size=page_size,
                            total_pages=1,
                        ),
                        None,
                    )

            query = (
                self.supabase.table("call_logs")
                .select("*", count="exact")
                .eq("organization_id", str(organization_id))
                .order("created_at", desc=True)
            )

            if agent_id:
                query = query.eq("agent_id", str(agent_id))
            if recording_call_ids is not None:
                query = query.in_("id", list(recording_call_ids))
            if status:
                query = query.eq("status", status)
            if source_type:
                query = query.eq("source_type", source_type)
            if date_from:
                query = query.gte("created_at", date_from.isoformat())
            if date_to_exclusive:
                query = query.lt("created_at", date_to_exclusive.isoformat())
            elif date_to:
                query = query.lte("created_at", date_to.isoformat())

            offset = (page - 1) * page_size
            query = query.range(offset, offset + page_size - 1)

            result = query.execute()
            total = result.count or 0
            rows = result.data or []
            if recording_call_ids is None and rows:
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
                    recording_call_ids = set()
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

    @tracer.start_as_current_span("call_logs.get_analytics")
    async def get_analytics(
        self,
        organization_id: Optional[UUID],
        *,
        period_days: int = 30,
        calendar_period: Optional[Literal["today", "yesterday"]] = None,
        call_status: Optional[str] = None,
        timezone_name: str = "UTC",
    ) -> Tuple[Optional[CallAnalytics], Optional[str]]:
        """Aggregate authorized call metrics for a rolling or calendar period.

        The report keeps its fixed 7-day and 30-day totals while charts, status
        totals, and agent snapshots use the selected rolling or calendar period.
        None organization_id means the platform-wide pulse; its hours are UTC.
        Returns (analytics, None) or (None, safe_error), never partial totals.
        """
        try:
            if period_days not in {7, 15, 30} or calendar_period not in {
                None,
                "today",
                "yesterday",
            }:
                return None, "Unsupported reporting period"
            report_timezone = ZoneInfo(
                timezone_name if organization_id is not None else "UTC"
            )
            now = datetime.now(timezone.utc)
            week_ago = now - timedelta(days=7)
            month_ago = now - timedelta(days=30)
            local_today = now.astimezone(report_timezone).date()
            calendar_date = None
            if calendar_period is not None:
                calendar_date = (
                    local_today
                    if calendar_period == "today"
                    else local_today - timedelta(days=1)
                )
                selected_start = datetime.combine(
                    calendar_date, time.min, tzinfo=report_timezone
                ).astimezone(timezone.utc)
                selected_end = (
                    now
                    if calendar_period == "today"
                    else datetime.combine(
                        local_today, time.min, tzinfo=report_timezone
                    ).astimezone(timezone.utc)
                )
            else:
                selected_start = now - timedelta(days=period_days)
                selected_end = now

            # Page narrow rows: PostgREST caps each response. Never return a
            # silently truncated total, and keep synchronous I/O off the loop.
            rows = []
            for offset in range(0, 100_000, 1000):
                query = (
                    self.supabase.table("call_logs")
                    .select(
                        "id,organization_id,agent_id,created_at,duration,status,source_type"
                    )
                    .gte("created_at", month_ago.isoformat())
                    .lt("created_at", now.isoformat())
                    .order("created_at")
                    .order("id")
                    .range(offset, offset + 999)
                )
                if organization_id is not None:
                    query = query.eq("organization_id", str(organization_id))
                result = await asyncio.to_thread(query.execute)
                batch = result.data or []
                rows.extend(batch)
                if len(batch) < 1000:
                    break
            else:
                return None, "Analytics volume exceeds the supported reporting limit"

            parsed_rows = []
            available_statuses = set()
            for row in rows:
                created = datetime.fromisoformat(
                    row["created_at"].replace("Z", "+00:00")
                )
                row_status = row.get("status", "unknown")
                available_statuses.add(row_status)
                duration = row.get("duration")
                parsed_rows.append((row, created, row_status, duration))

            selected_rows = [
                (row, created, row_status, duration)
                for row, created, row_status, duration in parsed_rows
                if selected_start <= created < selected_end
                and (call_status is None or row_status == call_status)
            ]
            completed_durations = [
                duration
                for _, _, row_status, duration in selected_rows
                if row_status == "completed" and duration is not None
            ]
            selected_average_duration = (
                round(sum(completed_durations) / len(completed_durations), 1)
                if completed_durations
                else None
            )

            calls_by_agent: dict = defaultdict(
                lambda: {
                    "count": 0,
                    "agent_id": None,
                    "agent_name": "Unknown",
                    "completed_durations": [],
                    "last_call_at": None,
                    "last_call_status": None,
                    "last_call_duration_seconds": None,
                    "last_call_source_type": None,
                }
            )
            calls_by_hour: dict = defaultdict(int)
            calls_by_status: dict = defaultdict(int)
            calls_by_day: dict = defaultdict(int)

            for row, created, row_status, duration in selected_rows:
                agent_key = row.get("agent_id") or UNASSIGNED_AGENT_KEY
                agent = calls_by_agent[agent_key]
                agent["count"] += 1
                agent["agent_id"] = row.get("agent_id")
                if row_status == "completed" and duration is not None:
                    agent["completed_durations"].append(duration)
                agent["last_call_at"] = created.isoformat()
                agent["last_call_status"] = row_status
                agent["last_call_duration_seconds"] = row.get("duration")
                agent["last_call_source_type"] = row.get("source_type")

                local_created = created.astimezone(report_timezone)
                calls_by_hour[local_created.hour] += 1
                calls_by_day[local_created.date().isoformat()] += 1
                calls_by_status[row_status] += 1

            agent_ids = [
                agent_id
                for agent_id in calls_by_agent
                if agent_id != UNASSIGNED_AGENT_KEY
            ]
            agent_names: dict = {}
            for offset in range(0, len(agent_ids), 100):
                query = (
                    self.supabase.table("voice_agents")
                    .select("id, name")
                    .in_("id", agent_ids[offset : offset + 100])
                )
                if organization_id is not None:
                    query = query.eq("organization_id", str(organization_id))
                agents_result = await asyncio.to_thread(query.execute)
                agent_names.update(
                    {agent["id"]: agent["name"] for agent in (agents_result.data or [])}
                )

            for agent_id, agent in calls_by_agent.items():
                agent["agent_name"] = (
                    "Unassigned calls"
                    if agent_id == UNASSIGNED_AGENT_KEY
                    else agent_names.get(agent_id, "Unknown")
                )
                durations = agent["completed_durations"]
                agent["avg_duration_seconds"] = (
                    round(sum(durations) / len(durations), 1) if durations else None
                )
                del agent["completed_durations"]

            if calendar_date is not None:
                report_dates = [calendar_date]
            else:
                day_start = selected_start.astimezone(report_timezone).date()
                day_count = (local_today - day_start).days
                report_dates = [
                    day_start + timedelta(days=day) for day in range(day_count + 1)
                ]
            day_list = [
                {
                    "date": report_date.isoformat(),
                    "calls": calls_by_day.get(report_date.isoformat(), 0),
                }
                for report_date in report_dates
            ]
            hour_list = [
                {"hour": hour, "calls": calls_by_hour.get(hour, 0)}
                for hour in range(24)
            ]
            status_list = [
                {"status": row_status, "count": count}
                for row_status, count in sorted(calls_by_status.items())
            ]
            agent_list = sorted(
                calls_by_agent.values(), key=lambda row: row["count"], reverse=True
            )
            recorded_durations = [
                duration for *_, duration in parsed_rows if duration is not None
            ]

            return (
                CallAnalytics(
                    active_organizations=len({row["organization_id"] for row in rows}),
                    total_calls_week=sum(
                        1 for _, created, _, _ in parsed_rows if created >= week_ago
                    ),
                    total_calls_month=len(rows),
                    avg_duration_seconds=(
                        round(sum(recorded_durations) / len(recorded_durations), 1)
                        if recorded_durations
                        else 0.0
                    ),
                    calls_by_agent=agent_list,
                    calls_by_hour=hour_list,
                    calls_by_status=status_list,
                    selected_period_days=1 if calendar_period else period_days,
                    selected_status=call_status,
                    selected_total_calls=len(selected_rows),
                    selected_active_organizations=len(
                        {row["organization_id"] for row, _, _, _ in selected_rows}
                    ),
                    selected_average_duration_seconds=selected_average_duration,
                    calls_by_day=day_list,
                    available_statuses=sorted(available_statuses),
                ),
                None,
            )
        except Exception:
            logger.error("Error computing call analytics", exc_info=True)
            return None, "Call analytics unavailable"


call_log_service = CallLogService()
