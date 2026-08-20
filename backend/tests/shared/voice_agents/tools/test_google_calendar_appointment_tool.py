"""Contract tests for the native Google Calendar Appointment adapter."""

from shared.voice_agents.tools.base.platform_tool_registry import PlatformToolRegistry
from shared.voice_agents.tools.implementations.google_calendar_appointment import (
    GoogleCalendarAppointmentTool,
)


class TestGoogleCalendarAppointmentTool:
    """Ensure the native adapter exposes the same small contract as MCP."""

    def test_native_tool_is_cataloged_with_appointment_functions(self) -> None:
        """The native path must be discoverable by the standard registry."""
        registry = PlatformToolRegistry()
        registry.register_tools_from_package(
            "shared.voice_agents.tools.implementations"
        )

        tool_class = registry.get_tool_class("Google_calendar_appointment")
        functions = registry.get_tool_functions("Google_calendar_appointment")

        assert tool_class is not None
        assert tool_class().metadata.name == "Google_calendar_appointment"
        assert {function.__name__ for function in functions} == {
            "find_available_slots",
            "check_availability",
            "find_appointments",
            "create_appointment",
            "update_appointment",
            "cancel_appointment",
        }

    def test_model_guidance_distinguishes_create_from_update(self) -> None:
        """Tool documentation must steer detail changes to update, not create."""
        create_doc = GoogleCalendarAppointmentTool.create_appointment.__doc__ or ""
        update_doc = GoogleCalendarAppointmentTool.update_appointment.__doc__ or ""
        availability_doc = (
            GoogleCalendarAppointmentTool.check_availability.__doc__ or ""
        )

        assert "only when no existing appointment" in create_doc.lower()
        assert "adding" in update_doc.lower()
        assert "correcting" in update_doc.lower()
        assert "caller details" in update_doc.lower()
        assert "reschedul" in update_doc.lower()
        assert "extend" in update_doc.lower()
        assert "shorten" in update_doc.lower()
        assert "new_duration_minutes" in update_doc.lower()
        assert "new booking" in availability_doc.lower()
        assert "existing appointment" in availability_doc.lower()

    def test_update_description_directs_all_existing_appointment_changes(self) -> None:
        """The native schema must steer mutations to update, not availability."""
        registry = PlatformToolRegistry()
        registry.register_tools_from_package(
            "shared.voice_agents.tools.implementations"
        )
        function = next(
            item
            for item in registry.get_tool_functions("Google_calendar_appointment")
            if item.__name__ == "update_appointment"
        )
        description = " ".join(
            (function.__doc__ or "").lower().replace("`", "").split()
        )

        assert "reschedul" in description
        assert "extend" in description
        assert "shorten" in description
        assert "email" in description
        assert "do not call check_availability" in description
