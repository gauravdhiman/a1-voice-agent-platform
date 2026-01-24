"""Cal.com tool for scheduling and booking management."""

from datetime import datetime
from typing import Any, Optional

import httpx
from livekit.agents import RunContext
from pydantic import BaseModel, Field

from shared.voice_agents.tools.base.base_tool import (
    BaseConfig,
    BaseSensitiveConfig,
    BaseTool,
    ToolMetadata,
)


class CalComAuthConfig(BaseModel):
    """Cal.com API key authentication configuration."""
    provider: str = "api_key"


class CalComTool(BaseTool):
    class AuthConfig(CalComAuthConfig):
        provider: str = "api_key"

    class Config(BaseConfig):
        event_type_id: int = Field(
            default=0,
            description="Default event type ID for bookings",
        )
        user_timezone: str = Field(
            default="America/New_York",
            description="User's timezone in IANA format (e.g., 'Asia/Kolkata', 'America/New_York')",
        )

    class SensitiveConfig(BaseSensitiveConfig):
        api_key: str = ""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="CalCom",
            description="Schedule and manage bookings with Cal.com",
            requires_auth=True,
            auth_type="api_key",
            auth_config=self.AuthConfig().model_dump(),
            config_schema=self.Config.model_json_schema(),
        )

    def _get_headers(self, api_version: str = "2024-08-13") -> dict[str, str]:
        """
        Get headers for Cal.com API requests.

        Args:
            api_version: Cal.com API version

        Returns:
            Headers dictionary with Authorization
        """
        if not self.sensitive_config or not self.sensitive_config.api_key:
            raise ValueError("API key not configured")

        return {
            "Authorization": f"Bearer {self.sensitive_config.api_key}",
            "cal-api-version": api_version,
            "Content-Type": "application/json",
        }

    async def get_available_slots(
        self,
        context: RunContext,
        start_date: str,
        end_date: str,
        event_type_id: Optional[int] = None,
    ) -> dict[str, Any]:
        """
        Description:
            Get available time slots for booking on Cal.com.

        Instructions:
            Dates should be in YYYY-MM-DD format.
            Returns time slots in UTC format.
            If event_type_id is not provided, uses the default configured ID.

        Args:
            context: LiveKit RunContext with tool_config and sensitive_config
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            event_type_id: Optional specific event type ID to check
        """
        target_event_type_id = event_type_id or self.config.event_type_id
        if not target_event_type_id:
            return {"error": "Event Type ID is required. Please provide it or configure a default."}

        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.cal.com/v2/slots/available",
                headers=self._get_headers(),
                params={
                    "startTime": f"{start_date}T00:00:00Z",
                    "endTime": f"{end_date}T23:59:59Z",
                    "eventTypeId": str(target_event_type_id),
                },
            )
            if response.status_code == 404:
                return {"error": f"Event Type ID {target_event_type_id} not found. Use list_event_types to find valid IDs."}
            
            response.raise_for_status()
            data = response.json()

            slots = data.get("data", {}).get("slots", {})
            available_slots = []
            for date, times in slots.items():
                for slot in times:
                    available_slots.append(slot["time"])

            return {"slots": available_slots, "count": len(available_slots), "event_type_id": target_event_type_id}

    async def list_event_types(
        self,
        context: RunContext,
    ) -> dict[str, Any]:
        """
        Description:
            List all available event types and their IDs from Cal.com.
            Use this to find the correct event_type_id for booking.

        Args:
            context: LiveKit RunContext
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.cal.com/v2/event-types",
                headers=self._get_headers(api_version="2024-06-14"),
            )
            response.raise_for_status()
            data = response.json()
            
            # Cal.com V2 API returns a list directly in the 'data' field
            event_types = data.get("data", [])
            result = []
            for et in event_types:
                result.append({
                    "id": et.get("id"),
                    "title": et.get("title"),
                    "slug": et.get("slug"),
                    "length": et.get("lengthInMinutes"),
                    "description": et.get("description")
                })
            
            return {"event_types": result, "count": len(result)}

    async def create_booking(
        self,
        context: RunContext,
        start_time: str,
        name: str,
        email: str,
        event_type_id: Optional[int] = None,
    ) -> dict[str, Any]:
        """
        Description:
            Create a new booking on Cal.com.

        Instructions:
            start_time should be in ISO 8601 format (e.g., 2024-08-13T09:00:00Z).
            It MUST be in UTC timezone.
            Ensure attendee email is valid before creating booking.

        Args:
            context: LiveKit RunContext with tool_config and sensitive_config
            start_time: Start time in ISO 8601 format (UTC)
            name: Attendee's name
            email: Attendee's email
            event_type_id: Optional specific event type ID to book
        """
        target_event_type_id = event_type_id or self.config.event_type_id
        if not target_event_type_id:
            return {"error": "Event Type ID is required to create a booking."}

        # Normalize start_time to UTC ISO format with 'Z'
        try:
            dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            # Cal.com expects 'Z' suffix and UTC time
            utc_start_time = dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        except Exception as e:
            return {"error": f"Invalid start_time format: {str(e)}. Use YYYY-MM-DDTHH:MM:SSZ"}

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.cal.com/v2/bookings",
                headers=self._get_headers(),
                json={
                    "start": utc_start_time,
                    "eventTypeId": int(target_event_type_id),
                    "attendee": {
                        "name": name, 
                        "email": email, 
                        "timeZone": self.config.user_timezone or "UTC"
                    },
                },
            )
            
            if response.status_code != 201:
                try:
                    error_data = response.json()
                    return {"error": f"Cal.com API error: {error_data.get('message', response.text)}"}
                except Exception:
                    return {"error": f"Cal.com API error ({response.status_code}): {response.text}"}

            booking_data = response.json().get("data", {})

            return {
                "booking_id": booking_data.get("id"),
                "uid": booking_data.get("uid"),
                "status": booking_data.get("status"),
                "start": booking_data.get("start"),
            }

    async def get_upcoming_bookings(
        self,
        context: RunContext,
        email: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Description:
            Get all upcoming bookings from Cal.com.

        Instructions:
            Optionally filter by attendee email for specific user's bookings.
            Returns only bookings with "upcoming" status.

        Args:
            context: LiveKit RunContext with tool_config and sensitive_config
            email: Optional attendee email to filter bookings

        Returns:
            Dict containing list of upcoming bookings

        Example:
            ```python
            # Get all upcoming bookings
            result = await get_upcoming_bookings(context)

            # Get bookings for specific email
            result = await get_upcoming_bookings(context, email="john@example.com")
            ```
        """
        if not self.sensitive_config or not self.sensitive_config.api_key:
            raise ValueError("API key not configured")

        async with httpx.AsyncClient() as client:
            params = {"status": "upcoming"}
            if email:
                params["attendeeEmail"] = email

            response = await client.get(
                "https://api.cal.com/v2/bookings",
                headers=self._get_headers(),
                params=params,
            )
            response.raise_for_status()
            bookings = response.json().get("data", [])

            if not bookings:
                return {"bookings": [], "message": "No upcoming bookings found."}

            booking_info = []
            for booking in bookings:
                booking_info.append(
                    {
                        "uid": booking.get("uid"),
                        "title": booking.get("title"),
                        "start": booking.get("start"),
                        "status": booking.get("status"),
                    }
                )

            return {"bookings": booking_info, "count": len(booking_info)}

    async def reschedule_booking(
        self,
        context: RunContext,
        booking_uid: str,
        new_start_time: str,
        reason: str,
    ) -> dict[str, Any]:
        """
        Description:
            Reschedule an existing booking on Cal.com.

        Instructions:
            booking_uid must be a valid Cal.com booking UID.
            new_start_time should be in ISO 8601 format (UTC).
            Provide a clear reason for the rescheduling.

        Args:
            context: LiveKit RunContext with tool_config and sensitive_config
            booking_uid: Booking UID to reschedule
            new_start_time: New start time in ISO 8601 format (UTC)
            reason: Reason for rescheduling
        """
        if not self.sensitive_config or not self.sensitive_config.api_key:
            raise ValueError("API key not configured")

        # Normalize new_start_time to UTC ISO format with 'Z'
        try:
            dt = datetime.fromisoformat(new_start_time.replace("Z", "+00:00"))
            utc_new_start_time = dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        except Exception as e:
            return {"error": f"Invalid new_start_time format: {str(e)}. Use YYYY-MM-DDTHH:MM:SSZ"}

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.cal.com/v2/bookings/{booking_uid}/reschedule",
                headers=self._get_headers(),
                json={
                    "start": utc_new_start_time,
                    "reschedulingReason": reason,
                },
            )
            
            if response.status_code != 201:
                try:
                    error_data = response.json()
                    return {"error": f"Cal.com API error: {error_data.get('message', response.text)}"}
                except Exception:
                    return {"error": f"Cal.com API error ({response.status_code}): {response.text}"}

            booking_data = response.json().get("data", {})

            return {
                "booking_id": booking_data.get("id"),
                "uid": booking_data.get("uid"),
                "start": booking_data.get("start"),
            }

    async def cancel_booking(
        self,
        context: RunContext,
        booking_uid: str,
        reason: str,
    ) -> dict[str, Any]:
        """
        Description:
            Cancel an existing booking on Cal.com.

        Instructions:
            booking_uid must be a valid Cal.com booking UID.
            Provide a clear cancellation reason for records.
            This action cannot be undone.

        Args:
            context: LiveKit RunContext with tool_config and sensitive_config
            booking_uid: Booking UID to cancel
            reason: Reason for cancellation

        Returns:
            Dict with cancellation confirmation

        Example:
            ```python
            result = await cancel_booking(
                context,
                "booking-uid-123",
                "Client cancelled the meeting"
            )
            # Returns: {"success": true, "message": "Booking cancelled successfully."}
            ```
        """
        if not self.sensitive_config or not self.sensitive_config.api_key:
            raise ValueError("API key not configured")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.cal.com/v2/bookings/{booking_uid}/cancel",
                headers=self._get_headers(),
                json={"cancellationReason": reason},
            )
            response.raise_for_status()

            return {
                "success": True,
                "message": "Booking cancelled successfully.",
                "booking_uid": booking_uid,
            }
