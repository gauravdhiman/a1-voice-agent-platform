import httpx
from typing import Any
from datetime import datetime, timedelta

from livekit.agents import function_tool, RunContext
from shared.voice_agents.tools.base.base_tool import BaseTool, ToolMetadata


class GoogleCalendarTool(BaseTool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="Google_calendar",
            description="Manage Google Calendar events, check availability, and schedule meetings.",
            requires_auth=True,
            auth_type="oauth2",
            auth_config={
                "provider": "google",
                "scopes": ["https://www.googleapis.com/auth/calendar.events", "https://www.googleapis.com/auth/calendar.readonly"],
                "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
                "token_url": "https://oauth2.googleapis.com/token"
            },
            config_schema={
                "type": "object",
                "properties": {
                    "calendar_id": {
                        "type": "string",
                        "title": "Calendar ID",
                        "default": "primary",
                        "description": "The ID of the calendar to use (e.g., 'primary' or an email address)."
                    },
                    "default_event_duration": {
                        "type": "integer",
                        "title": "Default Event Duration (minutes)",
                        "default": 30
                    }
                },
                "required": ["calendar_id"]
            }
        )

    @function_tool()
    async def list_events(
        self,
        context: RunContext,
        time_min: str,
        time_max: str | None = None,
        max_results: int = 10
    ) -> dict[str, Any]:
        """
        List calendar events within a time range.

        Args:
            context: LiveKit RunContext with tool_config and sensitive_config
            time_min: Start of time range in ISO format (e.g., 2025-12-30T09:00:00Z)
            time_max: End of time range in ISO format (optional)
            max_results: Maximum number of events to return (default: 10)
        """
        calendar_id = context.userdata.get("tool_config", {}).get("calendar_id", "primary")
        access_token = context.userdata.get("sensitive_config", {}).get("access_token")

        if not access_token:
            raise ValueError("No access token found in context")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events",
                headers=headers,
                params={
                    "timeMin": time_min,
                    "timeMax": time_max,
                    "maxResults": max_results,
                    "singleEvents": "true",
                    "orderBy": "startTime"
                }
            )
            response.raise_for_status()
            data = response.json()
            return {"events": data.get("items", [])}

    @function_tool()
    async def create_event(
        self,
        context: RunContext,
        title: str,
        start_time: str,
        duration_minutes: int = 30,
        attendees: list[str] | None = None,
        description: str = ""
    ) -> dict[str, Any]:
        """
        Create a new calendar event.

        Args:
            context: LiveKit RunContext with tool_config and sensitive_config
            title: Event title
            start_time: Event start time in ISO format
            duration_minutes: Duration in minutes (default: 30 from config)
            attendees: List of attendee email addresses (optional)
            description: Event description (optional)
        """
        calendar_id = context.userdata.get("tool_config", {}).get("calendar_id", "primary")
        access_token = context.userdata.get("sensitive_config", {}).get("access_token")
        default_duration = context.userdata.get("tool_config", {}).get("default_event_duration", 30)

        if not access_token:
            raise ValueError("No access token found in context")

        event = {
            "summary": title,
            "description": description,
            "start": {"dateTime": start_time},
            "end": {
                "dateTime": (
                    datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                    + timedelta(minutes=duration_minutes)
                ).isoformat()
            }
        }

        if attendees:
            event["attendees"] = [{"email": email} for email in attendees]

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events",
                headers=headers,
                json=event
            )
            response.raise_for_status()
            return response.json()

    @function_tool()
    async def check_availability(
        self,
        context: RunContext,
        date: str,
        duration_minutes: int = 30
    ) -> dict[str, Any]:
        """
        Check if time slots are free.

        Args:
            context: LiveKit RunContext with tool_config and sensitive_config
            date: Date and time to check in ISO format
            duration_minutes: Duration to check in minutes (default: 30)
        """
        calendar_id = context.userdata.get("tool_config", {}).get("calendar_id", "primary")
        access_token = context.userdata.get("sensitive_config", {}).get("access_token")
        default_duration = context.userdata.get("tool_config", {}).get("default_event_duration", 30)

        if not access_token:
            raise ValueError("No access token found in context")

        end_dt = (
            datetime.fromisoformat(date.replace("Z", "+00:00"))
            + timedelta(minutes=duration_minutes)
        ).isoformat()

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events",
                headers=headers,
                params={
                    "timeMin": date,
                    "timeMax": end_dt,
                    "singleEvents": "true",
                    "orderBy": "startTime"
                }
            )
            response.raise_for_status()
            data = response.json()

            has_conflict = len(data.get("items", [])) > 0
            return {
                "available": not has_conflict,
                "conflicts": data.get("items", [])
            }
