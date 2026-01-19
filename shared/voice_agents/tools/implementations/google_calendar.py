from datetime import datetime, timedelta
from typing import Any, Optional

import httpx
from livekit.agents import RunContext
from pydantic import Field

from shared.voice_agents.tools.base.auth_config import GoogleAuthConfig
from shared.voice_agents.tools.base.base_tool import (
    BaseConfig,
    BaseSensitiveConfig,
    BaseTool,
    ToolMetadata,
)


class GoogleCalendarTool(BaseTool):
    class AuthConfig(GoogleAuthConfig):
        scopes: list[str] = [
            "https://www.googleapis.com/auth/calendar.events",
            "https://www.googleapis.com/auth/calendar.readonly",
        ]
        auth_url: str = "https://accounts.google.com/o/oauth2/v2/auth"
        token_url: str = "https://oauth2.googleapis.com/token"

    class Config(BaseConfig):
        calendar_id: str = Field(
            default="primary",
            description=(
                "The ID of calendar to use (e.g., 'primary' or an email address)"
            ),
        )
        default_event_duration: int = Field(
            default=30, description="Default event duration in minutes"
        )

    class SensitiveConfig(BaseSensitiveConfig):
        access_token: str = ""
        refresh_token: Optional[str] = None
        token_expiry: Optional[str] = None

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="Google_calendar",
            description=(
                "Manage Google Calendar events, check availability, and "
                "schedule meetings."
            ),
            requires_auth=True,
            auth_type="oauth2",
            auth_config=self.AuthConfig().model_dump(),
            config_schema=self.Config.model_json_schema(),
        )

    async def list_events(
        self,
        context: RunContext,
        time_min: str,
        time_max: str | None = None,
        max_results: int = 10,
    ) -> dict[str, Any]:
        """
        List calendar events within a time range.
        Important points to consider:
        1. For time related parameters always pass the time in ISO format
        with timezone (e.g., 2025-12-30T09:00:00Z). If you do not have
        timezone or cannot infer it, always ask user to provide it.

        Args:
            context: LiveKit RunContext with tool_config and sensitive_config
            time_min: Start of time range in ISO format (e.g., 2025-12-30T09:00:00Z)
            time_max: End of time range in ISO format (optional)
            max_results: Maximum number of events to return (default: 10)
        """
        if not self.sensitive_config or not self.sensitive_config.access_token:
            raise ValueError("No access token found in sensitive config")

        headers = {
            "Authorization": f"Bearer {self.sensitive_config.access_token}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://www.googleapis.com/calendar/v3/calendars/{self.config.calendar_id}/events",  # noqa: E501
                headers=headers,
                params={
                    "timeMin": time_min,
                    "timeMax": time_max,
                    "maxResults": max_results,
                    "singleEvents": "true",
                    "orderBy": "startTime",
                },
            )
            response.raise_for_status()
            data = response.json()
            return {"events": data.get("items", [])}

    async def create_event(
        self,
        context: RunContext,
        title: str,
        start_time: str,
        duration_minutes: int = 30,
        attendees: list[str] | None = None,
        description: str | None = None,
    ) -> dict[str, Any]:
        """
        Create a new calendar event.
        Important points to consider:
        1. In case user provides attendees email ids, always confirm
        each one of them by spelling them letter by letter like for
        test.email-1@example.com, the spelling is
        T-E-S-T-DOT-E-M-A-I-L-DASH-1@-EXAMPLE-DOT-COM.
        2. Once user confirm all the details, then only create the event.
        3. For time parameters always pass the time in ISO format
        with timezone (e.g., 2025-12-30T09:00:00Z). If you do not
        have timezone or cannot infer it, always ask user to provide it.
        4. Before creating the event, always check the availability of
        that timeslot on calendar using check_availability tool (if available).

        Args:
            context: LiveKit RunContext with tool_config and sensitive_config
            title: Event title
            start_time: Event start time in ISO format
            duration_minutes: Duration in minutes (default: 30 from config)
            attendees: List of attendee email addresses (optional). Its option,
            but prefer asking it to the user.
            description: Event description (optional)
        """
        if not self.sensitive_config or not self.sensitive_config.access_token:
            raise ValueError("No access token found in sensitive config")

        event = {
            "summary": title,
            "description": description,
            "start": {"dateTime": start_time},
            "end": {
                "dateTime": (
                    datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                    + timedelta(minutes=duration_minutes)
                ).isoformat()
            },
        }

        if attendees:
            event["attendees"] = [{"email": email} for email in attendees]

        headers = {
            "Authorization": f"Bearer {self.sensitive_config.access_token}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://www.googleapis.com/calendar/v3/calendars/{self.config.calendar_id}/events",  # noqa: E501
                headers=headers,
                json=event,
            )
            response.raise_for_status()
            return response.json()

    async def update_event(
        self,
        context: RunContext,
        event_id: str,
        title: str | None = None,
        start_time: str | None = None,
        duration_minutes: int | None = None,
        attendees: list[str] | None = None,
        description: str | None = None,
    ) -> dict[str, Any]:
        """
        Update an existing calendar event.
        Important points to consider:
        1. Before updating an event, always use the list_events tool to
        check availability and identify the correct event to update. This
        ensures you're updating the right appointment.
        2. In case user provides attendees email ids, always confirm
        each one of them by spelling them letter by letter like for
        test.email-1@example.com, the spelling is
        T-E-S-T-DOT-E-M-A-I-L-DASH-1@-EXAMPLE-DOT-COM.
        3. Once user confirm all the details, then only update the event.
        4. For time parameters always pass the time in ISO format
        with timezone (e.g., 2025-12-30T09:00:00Z). If you do not
        have timezone or cannot infer it, always ask user to provide it.

        Args:
            context: LiveKit RunContext with tool_config and sensitive_config
            event_id: The ID of the event to update
            title: New event title (optional)
            start_time: New event start time in ISO format (optional)
            duration_minutes: New duration in minutes (optional, requires start_time)
            attendees: List of attendee email addresses (optional)
            description: New event description (optional)
        """
        if not self.sensitive_config or not self.sensitive_config.access_token:
            raise ValueError("No access token found in sensitive config")

        event = {}
        if title is not None:
            event["summary"] = title
        if description is not None:
            event["description"] = description
        if start_time is not None:
            event["start"] = {"dateTime": start_time}
            if duration_minutes is not None:
                event["end"] = {
                    "dateTime": (
                        datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                        + timedelta(minutes=duration_minutes)
                    ).isoformat()
                }
        if attendees is not None:
            event["attendees"] = [{"email": email} for email in attendees]

        headers = {
            "Authorization": f"Bearer {self.sensitive_config.access_token}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"https://www.googleapis.com/calendar/v3/calendars/{self.config.calendar_id}/events/{event_id}",  # noqa: E501
                headers=headers,
                json=event,
            )
            response.raise_for_status()
            return response.json()

    async def delete_event(self, context: RunContext, event_id: str) -> dict[str, Any]:
        """
        Delete a calendar event.
        Important points to consider:
        1. Before deleting an event, always use the list_events tool
        to identify the correct event to delete. This ensures you're
        deleting the right appointment.

        Args:
            context: LiveKit RunContext with tool_config and sensitive_config
            event_id: The ID of the event to delete

        Returns:
            Confirmation message
        """
        if not self.sensitive_config or not self.sensitive_config.access_token:
            raise ValueError("No access token found in sensitive config")

        headers = {
            "Authorization": f"Bearer {self.sensitive_config.access_token}",
        }

        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"https://www.googleapis.com/calendar/v3/calendars/{self.config.calendar_id}/events/{event_id}",  # noqa: E501
                headers=headers,
            )
            response.raise_for_status()
            return {"success": True, "message": "Event deleted successfully"}

    async def check_availability(
        self, context: RunContext, date: str, duration_minutes: int = 30
    ) -> dict[str, Any]:
        """
        Check if time slots are free.
        Important points to consider:
        2. For date and time related parameters always pass the time in ISO
        format with timezone (e.g., 2025-12-30T09:00:00Z). If you do
        not have timezone, always ask user to provide it.

        Args:
            context: LiveKit RunContext with tool_config and sensitive_config
            date: Date and time to check in ISO format
            duration_minutes: Duration to check in minutes (default: 30)
        """
        if not self.sensitive_config or not self.sensitive_config.access_token:
            raise ValueError("No access token found in sensitive config")

        end_dt = (
            datetime.fromisoformat(date.replace("Z", "+00:00"))
            + timedelta(minutes=duration_minutes)
        ).isoformat()

        headers = {
            "Authorization": f"Bearer {self.sensitive_config.access_token}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://www.googleapis.com/calendar/v3/calendars/{self.config.calendar_id}/events",  # noqa: E501
                headers=headers,
                params={
                    "timeMin": date,
                    "timeMax": end_dt,
                    "singleEvents": "true",
                    "orderBy": "startTime",
                },
            )
            response.raise_for_status()
            data = response.json()

            has_conflict = len(data.get("items", [])) > 0
            return {"available": not has_conflict, "conflicts": data.get("items", [])}
