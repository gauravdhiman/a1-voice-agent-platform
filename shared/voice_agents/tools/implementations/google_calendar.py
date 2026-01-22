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
        Description:
            Retrieve all calendar events within a specified time range.

        Instructions:
            Always include timezone in ISO format timestamps.
            Ask user for timezone if not provided or inferable.
            Default to 10 events, ask for more if needed.

        Args:
            context: LiveKit RunContext with tool_config and sensitive_config
            time_min: Start of time range in ISO format (e.g., 2025-12-30T09:00:00Z), with timezone
            time_max: End of time range in ISO format (optional), with timezone
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
        Description:
            Schedule a new event on the user's Google Calendar.

        Instructions:
            1. Always spell out attendee emails for verification.
            For instance test.email-1@example.com, the spelling is T-E-S-T-DOT-E-M-A-I-L-DASH-1@-EXAMPLE-DOT-COM
            2. Check availability before booking if check_availability tool is available.
            3. Always pass the time in ISO format
            with timezone (e.g., 2025-12-30T09:00:00Z). If you do not
            have timezone or cannot infer it, always ask user to provide it.
            4. Confirm all details with user before creating the event.
            DO NOT CREATE EVENT WITHOUT USER EXPLICIT CONFIRMATION.

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
        Description:
            Modify details of an existing calendar event.

        Instructions:
            - Use list_events to find the correct event first.
            - Always spell out attendee emails for verification.
            For instance test.email-1@example.com, the spelling is T-E-S-T-DOT-E-M-A-I-L-DASH-1@-EXAMPLE-DOT-COM
            - Always pass the time in ISO format
            with timezone (e.g., 2025-12-30T09:00:00Z). If you do not
            have timezone or cannot infer it, always ask user to provide it.
            - Confirm all details with user before creating the event.
            DO NOT CREATE EVENT WITHOUT USER EXPLICIT CONFIRMATION.

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
        Description:
            Remove / Delete an event from the user's Google Calendar.

        Instructions:
            - Use list_events to verify the correct event before deletion.
            - Confirm with user that they want to delete this specific event.
            as this action cannot be undone.

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

    async def get_event(self, context: RunContext, event_id: str) -> dict[str, Any]:
        """
        Description:
            Get detailed information about a specific calendar event.

        Instructions:
            Use when user needs to see full event details.
            Helpful for verifying event information before updates.

        Args:
            context: LiveKit RunContext with tool_config and sensitive_config
            event_id: ID of event to retrieve

            Returns:
            Dict with event details
        """
        if not self.sensitive_config or not self.sensitive_config.access_token:
            raise ValueError("No access token found in sensitive config")

        headers = {
            "Authorization": f"Bearer {self.sensitive_config.access_token}",
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://www.googleapis.com/calendar/v3/calendars/{self.config.calendar_id}/events/{event_id}",  # noqa: E501
                headers=headers,
            )
            response.raise_for_status()
            event_data = response.json()

            return {
                "event_id": event_id,
                "event": event_data,
            }

    async def check_availability(
        self, context: RunContext, date: str, duration_minutes: int = 30
    ) -> dict[str, Any]:
        """
        Description:
            Check if a time slot is available on the calendar.

        Instructions:
            - Always include timezone in ISO format timestamps.
            - Ask user for timezone if not provided or inferable.
            - Use before creating or updating events to avoid double-booking.

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
