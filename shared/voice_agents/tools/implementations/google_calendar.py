import httpx
from typing import Any, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field

from livekit.agents import function_tool, RunContext
from shared.voice_agents.tools.base.base_tool import (
    BaseTool,
    ToolMetadata,
    BaseConfig,
    BaseAuthConfig,
    BaseSensitiveConfig
)


class GoogleCalendarTool(BaseTool):
    class AuthConfig(BaseAuthConfig):
        provider: str = "google"
        scopes: list[str] = [
            "https://www.googleapis.com/auth/calendar.events",
            "https://www.googleapis.com/auth/calendar.readonly"
        ]
        auth_url: str = "https://accounts.google.com/o/oauth2/v2/auth"
        token_url: str = "https://oauth2.googleapis.com/token"
        access_type: str = "offline"  # Required to get refresh_token
        prompt: str = "consent"  # Required to get refresh_token

    class Config(BaseConfig):
        calendar_id: str = Field(default="primary", description="The ID of calendar to use (e.g., 'primary' or an email address)")
        default_event_duration: int = Field(default=30, description="Default event duration in minutes")

    class SensitiveConfig(BaseSensitiveConfig):
        access_token: str = ""
        refresh_token: Optional[str] = None
        token_expiry: Optional[str] = None

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="Google_calendar",
            description="Manage Google Calendar events, check availability, and schedule meetings.",
            requires_auth=True,
            auth_type="oauth2",
            auth_config=self.AuthConfig().model_dump(),
            config_schema=self.Config.model_json_schema()
        )

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
        if not self.sensitive_config or not self.sensitive_config.access_token:
            raise ValueError("No access token found in sensitive config")

        headers = {
            "Authorization": f"Bearer {self.sensitive_config.access_token}",
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://www.googleapis.com/calendar/v3/calendars/{self.config.calendar_id}/events",
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

    async def create_event(
        self,
        context: RunContext,
        title: str,
        start_time: str,
        duration_minutes: int = 30,
        attendees: list[str] | None = None,
        description: str | None = None
    ) -> dict[str, Any]:
        """
        Create a new calendar event.
        In case user provides attendees email ids, always confirm each one of them by spelling them letter by letter like for test.email-1@example.com, the spelling is T-E-S-T-DOT-E-M-A-I-L-DASH-1@-EXAMPLE-DOT-COM.
        Once user confirm all the details, then only create the event.

        Args:
            context: LiveKit RunContext with tool_config and sensitive_config
            title: Event title
            start_time: Event start time in ISO format
            duration_minutes: Duration in minutes (default: 30 from config)
            attendees: List of attendee email addresses (optional). Its option, but prefer asking it to the user.
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
            }
        }

        if attendees:
            event["attendees"] = [{"email": email} for email in attendees]

        headers = {
            "Authorization": f"Bearer {self.sensitive_config.access_token}",
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://www.googleapis.com/calendar/v3/calendars/{self.config.calendar_id}/events",
                headers=headers,
                json=event
            )
            response.raise_for_status()
            return response.json()

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
        if not self.sensitive_config or not self.sensitive_config.access_token:
            raise ValueError("No access token found in sensitive config")

        end_dt = (
            datetime.fromisoformat(date.replace("Z", "+00:00"))
            + timedelta(minutes=duration_minutes)
        ).isoformat()

        headers = {
            "Authorization": f"Bearer {self.sensitive_config.access_token}",
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://www.googleapis.com/calendar/v3/calendars/{self.config.calendar_id}/events",
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
