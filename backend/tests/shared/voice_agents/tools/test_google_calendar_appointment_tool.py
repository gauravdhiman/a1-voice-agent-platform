"""Contract tests for the native Google Calendar Appointment adapter."""

from shared.voice_agents.tools.base.platform_tool_registry import PlatformToolRegistry


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
