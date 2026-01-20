"""Tests for LiveKit tool registry."""
import pytest
from unittest.mock import Mock, patch


class TestLiveKitToolRegistry:
    """Test cases for LiveKitToolRegistry."""

    @pytest.fixture
    def registry(self):
        """Get the LiveKit tool registry instance."""
        from shared.voice_agents.tools.base.registry_livekit import (
            livekit_tool_registry,
        )

        return livekit_tool_registry

    def test_registry_instance_exists(self, registry):
        """Test registry instance exists."""
        assert registry is not None
        assert hasattr(registry, "_tools")
        assert hasattr(registry, "_functions")

    def test_register_tools_from_package(self, registry):
        """Test registering tools from package."""
        initial_count = len(registry._tools)

        # Register tools from package
        registry.register_tools_from_package(
            "shared.voice_agents.tools.implementations"
        )

        # Verify tools were registered
        assert len(registry._tools) >= initial_count

    def test_get_tool_class(self, registry):
        """Test getting tool class by name."""
        # Register tools first
        registry.register_tools_from_package(
            "shared.voice_agents.tools.implementations"
        )

        # Try to get Google Calendar tool
        calendar_class = registry.get_tool_class("Google_calendar")
        assert calendar_class is not None
        assert calendar_class.__name__ == "GoogleCalendarTool"

        # Try to get Gmail tool
        gmail_class = registry.get_tool_class("Gmail")
        assert gmail_class is not None
        assert gmail_class.__name__ == "GmailTool"

    def test_get_tool_class_not_found(self, registry):
        """Test getting non-existent tool class."""
        # Register tools first
        registry.register_tools_from_package(
            "shared.voice_agents.tools.implementations"
        )

        # Try to get non-existent tool
        tool_class = registry.get_tool_class("NonExistentTool")
        assert tool_class is None

    def test_get_tool_functions(self, registry):
        """Test getting tool functions."""
        # Register tools first
        registry.register_tools_from_package(
            "shared.voice_agents.tools.implementations"
        )

        # Get functions for Google Calendar
        calendar_functions = registry.get_tool_functions("Google_calendar")
        assert calendar_functions is not None
        assert len(calendar_functions) > 0

        # Get functions for Gmail
        gmail_functions = registry.get_tool_functions("Gmail")
        assert gmail_functions is not None
        assert len(gmail_functions) > 0

    def test_get_tool_functions_not_found(self, registry):
        """Test getting functions for non-existent tool."""
        # Register tools first
        registry.register_tools_from_package(
            "shared.voice_agents.tools.implementations"
        )

        # Try to get functions for non-existent tool
        functions = registry.get_tool_functions("NonExistentTool")
        assert functions == []

    def test_get_tool_names(self, registry):
        """Test getting all tool names."""
        # Register tools first
        registry.register_tools_from_package(
            "shared.voice_agents.tools.implementations"
        )

        # Get tool names
        tool_names = registry.get_tool_names()
        assert tool_names is not None
        assert isinstance(tool_names, list)
        assert len(tool_names) >= 2
        assert "Google_calendar" in tool_names
        assert "Gmail" in tool_names

    def test_tool_has_metadata(self, registry):
        """Test registered tools have metadata."""
        # Register tools first
        registry.register_tools_from_package(
            "shared.voice_agents.tools.implementations"
        )

        # Get Google Calendar tool
        calendar_class = registry.get_tool_class("Google_calendar")
        assert calendar_class is not None

        # Create instance and check metadata
        tool_instance = calendar_class(config={}, sensitive_config={})
        assert hasattr(tool_instance, "metadata")
        assert tool_instance.metadata is not None

    def test_google_calendar_functions(self, registry):
        """Test Google Calendar tool has expected functions."""
        # Register tools first
        registry.register_tools_from_package(
            "shared.voice_agents.tools.implementations"
        )

        # Get functions
        functions = registry.get_tool_functions("Google_calendar")
        function_names = [f.__name__ for f in functions]

        # Check for expected functions
        expected_functions = [
            "check_availability",
            "create_event",
            "update_event",
            "delete_event",
            "list_events",
            "get_event",
        ]

        for expected in expected_functions:
            assert expected in function_names, f"Missing function: {expected}"

    def test_gmail_functions(self, registry):
        """Test Gmail tool has expected functions."""
        # Register tools first
        registry.register_tools_from_package(
            "shared.voice_agents.tools.implementations"
        )

        # Get functions
        functions = registry.get_tool_functions("Gmail")
        function_names = [f.__name__ for f in functions]

        # Check for core functions (actual implementation has more specific methods)
        expected_functions = [
            "send_email",
            "read_email",
            "search_emails",
            "delete_email",
            "get_latest_emails",
            "get_unread_emails",
        ]

        for expected in expected_functions:
            assert expected in function_names, f"Missing function: {expected}"

    def test_tool_instantiation(self, registry):
        """Test instantiating tool with config."""
        # Register tools first
        registry.register_tools_from_package(
            "shared.voice_agents.tools.implementations"
        )

        # Get Google Calendar tool class
        calendar_class = registry.get_tool_class("Google_calendar")

        # Instantiate with config
        config = {"calendar_id": "primary"}
        tool_instance = calendar_class(config=config, sensitive_config={})

        assert tool_instance is not None
        assert tool_instance.config.calendar_id == "primary"

    def test_tool_instantiation_with_sensitive_config(self, registry):
        """Test instantiating tool with sensitive config."""
        # Register tools first
        registry.register_tools_from_package(
            "shared.voice_agents.tools.implementations"
        )

        # Get Google Calendar tool class
        calendar_class = registry.get_tool_class("Google_calendar")

        # Instantiate with config and sensitive config
        config = {"calendar_id": "primary"}
        sensitive_config = {
            "access_token": "test-token",
            "refresh_token": "test-refresh",
        }
        tool_instance = calendar_class(
            config=config, sensitive_config=sensitive_config
        )

        assert tool_instance is not None
        assert tool_instance.sensitive_config.access_token == "test-token"

    def test_tool_instantiation_with_empty_config(self, registry):
        """Test instantiating tool with empty config."""
        # Register tools first
        registry.register_tools_from_package(
            "shared.voice_agents.tools.implementations"
        )

        # Get Google Calendar tool class
        calendar_class = registry.get_tool_class("Google_calendar")

        # Instantiate with empty config
        tool_instance = calendar_class(config={}, sensitive_config={})

        assert tool_instance is not None
        assert tool_instance.config.calendar_id == "primary"  # Default value

    def test_tool_functions_have_context_param(self, registry):
        """Test all tool functions have context parameter."""
        # Register tools first
        registry.register_tools_from_package(
            "shared.voice_agents.tools.implementations"
        )

        # Get Google Calendar functions
        functions = registry.get_tool_functions("Google_calendar")

        for func in functions:
            import inspect

            sig = inspect.signature(func)
            assert "context" in sig.parameters, f"Function {func.__name__} missing context param"

    def test_tool_functions_have_docstrings(self, registry):
        """Test all tool functions have docstrings."""
        # Register tools first
        registry.register_tools_from_package(
            "shared.voice_agents.tools.implementations"
        )

        # Get Google Calendar functions
        functions = registry.get_tool_functions("Google_calendar")

        for func in functions:
            assert func.__doc__ is not None, f"Function {func.__name__} missing docstring"
            assert len(func.__doc__) > 0, f"Function {func.__name__} has empty docstring"
