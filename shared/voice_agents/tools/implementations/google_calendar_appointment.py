"""Google Calendar appointment-booking tool for business agents."""

from typing import Any, Optional
from zoneinfo import ZoneInfo

from pydantic import Field

from shared.voice_agents.tools.base.auth_config import GoogleAuthConfig
from shared.voice_agents.tools.base.base_tool import (
    BaseConfig,
    BaseSensitiveConfig,
    BaseTool,
    ToolMetadata,
)
from shared.voice_agents.tools.base.tool_context import ToolContext
from shared.voice_agents.tools.google_calendar_appointment_service import (
    GoogleCalendarAppointmentService,
)


class GoogleCalendarAppointmentTool(BaseTool):
    """Expose the shared appointment service through native agent functions.

    This tool is intentionally separate from the legacy general-purpose
    ``Google_calendar`` tool.  Its model-facing contract is for business
    appointments only; it does not expose generic event CRUD or journal-style
    calendar management.
    """

    class AuthConfig(GoogleAuthConfig):
        """OAuth configuration required for Google Calendar appointments."""

        scopes: list[str] = [
            "https://www.googleapis.com/auth/calendar.events",
            "https://www.googleapis.com/auth/calendar.readonly",
        ]
        auth_url: str = "https://accounts.google.com/o/oauth2/v2/auth"
        token_url: str = "https://oauth2.googleapis.com/token"

    class Config(BaseConfig):
        """Organization-level appointment policy and calendar selection."""

        calendar_id: str = Field(
            default="primary",
            description="Google Calendar id used for appointments; do not ask the caller for it.",
        )
        timezone: Optional[str] = Field(
            default=None,
            description=(
                "Optional calendar-specific IANA timezone override. When unset, "
                "the organization timezone from the runtime is used."
            ),
        )
        require_phone: bool = Field(
            default=False,
            description="Require a caller phone number before booking.",
        )
        require_email: bool = Field(
            default=False,
            description="Require a caller email address before booking.",
        )

    class SensitiveConfig(BaseSensitiveConfig):
        """OAuth tokens stored encrypted by the platform."""

        access_token: str = ""
        refresh_token: Optional[str] = None
        token_expiry: Optional[str] = None

    @property
    def metadata(self) -> ToolMetadata:
        """Return the stable platform catalog metadata for this tool."""
        return ToolMetadata(
            name="Google_calendar_appointment",
            description=(
                "Find availability and book, update, or cancel business appointments "
                "on an organization's Google Calendar."
            ),
            requires_auth=True,
            auth_type="oauth2",
            auth_config=self.AuthConfig().model_dump(),
            config_schema=self.Config.model_json_schema(),
        )

    def _service(self, context: ToolContext) -> GoogleCalendarAppointmentService:
        """Build a service using organization-scoped runtime context."""
        timezone_name = self.config.timezone or context.organization_timezone or "UTC"
        # The organization resolver validates this before a session starts, but
        # keep the adapter defensive when it is called directly in a test or
        # another runtime.
        ZoneInfo(timezone_name)
        now_provider = None
        if context.current_time is not None:
            now_provider = lambda: context.current_time  # noqa: E731
        return GoogleCalendarAppointmentService(
            access_token=self.sensitive_config.access_token,
            calendar_id=self.config.calendar_id,
            timezone_name=timezone_name,
            require_phone=self.config.require_phone,
            require_email=self.config.require_email,
            now_provider=now_provider,
            idempotency_key=context.session_id,
        )

    async def find_available_slots(
        self,
        context: ToolContext,
        window_start: str,
        window_end: str,
        duration_minutes: int,
        slot_interval_minutes: int = 30,
    ) -> dict[str, Any]:
        """Find free starts in a time window for an appointment duration.

        Args:
            context: Trusted runtime context containing organization timezone.
            window_start: ISO 8601 timestamp with timezone for the search start.
            window_end: ISO 8601 timestamp with timezone for the search end.
            duration_minutes: Required appointment length from the business rule.
            slot_interval_minutes: Distance between candidate starts. The
                service aligns returned starts to local clock boundaries, so
                use the organization's normal interval (typically 15 or 30)
                rather than deriving one from the current minute.

        Returns:
            JSON-safe availability result with normalized slots and timezone.
        """
        return await self._service(context).find_available_slots(
            window_start=window_start,
            window_end=window_end,
            duration_minutes=duration_minutes,
            slot_interval_minutes=slot_interval_minutes,
        )

    async def check_availability(
        self, context: ToolContext, start_time: str, duration_minutes: int
    ) -> dict[str, Any]:
        """Check one exact future interval for a possible new appointment.

        Use this only when the caller is considering a new booking and there
        is no existing appointment being changed. Do not use it to reschedule,
        extend, shorten, or edit an existing appointment; use
        ``update_appointment`` with its appointment id for every existing-
        appointment change. Do not use this as a pre-check for an existing
        appointment because its own calendar event is busy by design;
        ``update_appointment`` excludes the appointment being changed.
        ``start_time`` must be an ISO 8601 datetime with a numeric timezone
        offset.

        Returns a result with ``status`` of ``available``, ``busy``, ``past``,
        or ``error``. Error results include an actionable ``error.next_action``
        and may identify the argument that must be corrected.
        """
        return await self._service(context).check_availability(
            start_time=start_time, duration_minutes=duration_minutes
        )

    async def find_appointments(
        self,
        context: ToolContext,
        window_start: str,
        window_end: str,
        caller_name: str = "",
        caller_phone: str = "",
        caller_email: str = "",
        limit: int = 20,
    ) -> dict[str, Any]:
        """Find existing appointments by time window and optional caller fields.

        Use this when the appointment id is not already in the conversation.
        Search is primarily temporal; caller name, phone, and email narrow the
        results but are not identity verification. Use the returned
        ``appointment.id`` with ``update_appointment`` or
        ``cancel_appointment``; never invent an id. Both window datetimes must
        include numeric timezone offsets, and no appointment should be
        invented when this returns an error or no match.
        """
        return await self._service(context).find_appointments(
            window_start=window_start,
            window_end=window_end,
            caller_name=caller_name,
            caller_phone=caller_phone,
            caller_email=caller_email,
            limit=limit,
        )

    async def create_appointment(
        self,
        context: ToolContext,
        caller_name: str,
        purpose: str,
        start_time: str,
        duration_minutes: int,
        user_confirmed: bool,
        caller_phone: str = "",
        caller_email: str = "",
        notes: str = "",
    ) -> dict[str, Any]:
        """Book a confirmed appointment after a fresh availability check.

        Use this only when no existing appointment satisfies the caller's
        request. Do not use it to add or correct contact details or reschedule
        an appointment already returned by a tool; use ``update_appointment``
        with the returned ``appointment.id`` instead. A same-session retry is
        handled idempotently by the service so it cannot create a duplicate.

        The caller's email is optional because organizations differ, but it is
        available as a first-class argument and can be made required through
        tool configuration.  Do not put date of birth, insurance data, or
        other sensitive health information in ``notes`` unless the
        organization's calendar-retention policy explicitly permits it.
        Set ``user_confirmed`` to true only after the caller confirms the final
        purpose, date, start time, duration, and required contact details.
        Datetimes must include a numeric timezone offset. On an error, follow
        the returned ``error.next_action`` and do not claim that booking
        succeeded.
        """
        return await self._service(context).create_appointment(
            caller_name=caller_name,
            purpose=purpose,
            start_time=start_time,
            duration_minutes=duration_minutes,
            caller_phone=caller_phone,
            caller_email=caller_email,
            notes=notes,
            user_confirmed=user_confirmed,
        )

    async def update_appointment(
        self,
        context: ToolContext,
        appointment_id: str,
        user_confirmed: bool,
        new_start_time: str = "",
        new_duration_minutes: int = 0,
        new_purpose: str = "",
        caller_name: str = "",
        caller_phone: str = "",
        caller_email: str = "",
        notes: str = "",
    ) -> dict[str, Any]:
        """Update an existing appointment after explicit caller confirmation.

        Use this function for every change to an existing appointment:
        rescheduling or moving it, extending or shortening it, changing the
        purpose or caller name, adding, replacing, or correcting an email or
        phone number and other caller details, and updating notes. Do not call
        ``check_availability`` to edit an
        existing appointment; this operation checks the proposed interval and
        excludes the appointment being changed from its own conflict check.
        Use the ``appointment_id`` returned by ``find_appointments`` or an
        earlier mutation, and never invent an id. ``new_duration_minutes`` is
        the final total duration, not the number of minutes to add or remove.
        Omit ``new_start_time`` to keep the current start time. Any supplied
        new start time must be ISO 8601 with a numeric timezone offset. Never
        call ``create_appointment`` for an existing booking.

        Set ``user_confirmed`` to true only after the caller confirms the
        requested change. A busy result means the new interval conflicts with
        another event; an error includes ``error.next_action``. Never claim an
        update succeeded without a successful ``updated`` result.
        """
        return await self._service(context).update_appointment(
            appointment_id=appointment_id,
            new_start_time=new_start_time,
            new_duration_minutes=new_duration_minutes,
            new_purpose=new_purpose,
            caller_name=caller_name,
            caller_phone=caller_phone,
            caller_email=caller_email,
            notes=notes,
            user_confirmed=user_confirmed,
        )

    async def cancel_appointment(
        self, context: ToolContext, appointment_id: str, user_confirmed: bool
    ) -> dict[str, Any]:
        """Cancel one existing appointment after explicit confirmation.

        Use the appointment id returned by ``find_appointments``. Set
        ``user_confirmed`` to true only after the caller confirms cancellation,
        and report success only after a ``cancelled`` result.
        """
        return await self._service(context).cancel_appointment(
            appointment_id=appointment_id, user_confirmed=user_confirmed
        )
