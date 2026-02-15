"""Tests for LiveKit tool registry."""

from unittest.mock import Mock, patch

import pytest


class TestLiveKitToolRegistry:
    """Test cases for LiveKitToolRegistry."""

    @pytest.fixture
    def registry(self):
        """Get the LiveKit tool registry instance."""
        from shared.voice_agents.tools.base.registry_livekit import \
            livekit_tool_registry

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
        tool_instance = calendar_class(config=config, sensitive_config=sensitive_config)

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
            assert (
                "context" in sig.parameters
            ), f"Function {func.__name__} missing context param"

    def test_tool_functions_have_docstrings(self, registry):
        """Test all tool functions have docstrings."""
        # Register tools first
        registry.register_tools_from_package(
            "shared.voice_agents.tools.implementations"
        )

        # Get Google Calendar functions
        functions = registry.get_tool_functions("Google_calendar")

        for func in functions:
            assert (
                func.__doc__ is not None
            ), f"Function {func.__name__} missing docstring"
            assert (
                len(func.__doc__) > 0
            ), f"Function {func.__name__} has empty docstring"

    def test_format_function_name(self, registry):
        """Test _format_function_name converts snake_case to Title Case."""
        # Test basic snake_case
        assert (
            registry._format_function_name("get_latest_emails") == "Get Latest Emails"
        )
        assert registry._format_function_name("send_email") == "Send Email"
        assert registry._format_function_name("read_email") == "Read Email"

        # Test with multiple underscores
        assert registry._format_function_name("search__emails") == "Search Emails"
        assert registry._format_function_name("get___latest") == "Get Latest"

        # Test single word
        assert registry._format_function_name("delete") == "Delete"

        # Test already has capitals
        assert registry._format_function_name("get_user_id") == "Get User Id"

    def test_schema_extraction_uses_formated_name_and_description(self, registry):
        """Test that _extract_schema_from_function uses formatted names and descriptions."""
        # Register tools first
        registry.register_tools_from_package(
            "shared.voice_agents.tools.implementations"
        )

        # Get Gmail functions
        functions = registry.get_tool_functions("Gmail")

        # Find a specific function (send_email)
        send_email_func = next(
            (f for f in functions if f.__name__ == "send_email"), None
        )
        assert send_email_func is not None

        # Extract schema
        schema = registry._extract_schema_from_function(send_email_func)

        # Verify name is formatted (Send Email, not send_email)
        assert schema is not None
        assert schema["name"] == "Send Email"

        # Verify description is from Description: section (1-3 lines only)
        assert "Args:" not in schema["description"]
        assert "Instructions:" not in schema["description"]
        assert "context:" not in schema["description"]
        assert "LiveKit RunContext" not in schema["description"]

    def test_extract_description_section(self, registry):
        """Test _extract_description_section extracts only Description: section."""
        docstring = """
        Get the latest emails from the user's inbox.

        Description:
            Retrieve the most recent emails from the user's Gmail inbox.

        Instructions:
            Always limit results to 5-10 emails unless user specifically requests more.
            This is for browsing recent emails, not for bulk operations.

        Args:
            context: LiveKit RunContext with tool_config and sensitive_config
            count: Number of latest emails to retrieve (default: 5, max: 10)

        Returns:
            Dict containing list of emails with details
        """
        expected = "Retrieve the most recent emails from the user's Gmail inbox."
        result = registry._extract_description_section(docstring)
        assert result == expected

    def test_extract_description_section_multiline(self, registry):
        """Test _extract_description_section with 2-3 line description."""
        docstring = """
        Send an email immediately. to and cc are comma separated string of email ids.

        Description:
            Compose and send an email to specified recipients immediately.
            Ensure subject line accurately reflects email content.

        Instructions:
            Always confirm email addresses with user before sending.
            Format body as plain text, not HTML.

        Args:
            context: LiveKit RunContext with tool_config and sensitive_config
            to: Comma separated string of recipient email addresses

        Returns:
            Dict containing sent email details including id
        """
        expected = """Compose and send an email to specified recipients immediately.
            Ensure subject line accurately reflects email content."""
        result = registry._extract_description_section(docstring)
        assert result == expected

    def test_extract_description_section_fallback(self, registry):
        """Test _extract_description_section falls back for old docstrings."""
        docstring = """
        Get the latest emails from the user's inbox.

        Args:
            context: LiveKit RunContext with tool_config and sensitive_config
            count: Number of latest emails to retrieve (default: 5, max: 10)

        Returns:
            Dict containing list of emails with details
        """
        expected = "Get the latest emails from the user's inbox."
        result = registry._extract_description_section(docstring)
        assert result == expected

    def test_extract_description_section_stops_at_instructions(self, registry):
        """Test _extract_description_section stops at Instructions section."""
        docstring = """
        Search emails based on a given query.

        Description:
            Search emails in inbox using natural language query.

        Instructions:
            Use specific keywords and filters for better results.
            Avoid overly broad queries that return too many results.

        Args:
            context: LiveKit RunContext with tool_config and sensitive_config
            query: Natural language query to search for

        Returns:
            Dict containing list of matching emails
        """
        expected = "Search emails in inbox using natural language query."
        result = registry._extract_description_section(docstring)
        assert result == expected
        assert "Instructions:" not in result

    def test_extract_before_first_section(self, registry):
        """Test _extract_before_first_section for backward compatibility."""
        docstring = """
        Create a draft email.

        This creates a draft in Gmail for later editing or sending.

        Args:
            context: LiveKit RunContext with tool_config and sensitive_config
            to: Comma separated string of recipient email addresses

        Returns:
            Draft ID
        """
        expected = """Create a draft email.

        This creates a draft in Gmail for later editing or sending."""
        result = registry._extract_before_first_section(docstring)
        assert result == expected
        assert "Args:" not in result

    def test_google_sheets_tool_registration(self, registry):
        """Test Google Sheets tool is properly registered."""
        # Register tools first
        registry.register_tools_from_package(
            "shared.voice_agents.tools.implementations"
        )

        # Check if Google Sheets tool is registered
        tool_class = registry.get_tool_class("Google_Sheets")
        assert tool_class is not None
        assert tool_class.__name__ == "GoogleSheetsTool"

        # Check tool names includes Google Sheets
        tool_names = registry.get_tool_names()
        assert "Google_Sheets" in tool_names

    def test_google_sheets_functions(self, registry):
        """Test Google Sheets tool has expected functions."""
        # Register tools first
        registry.register_tools_from_package(
            "shared.voice_agents.tools.implementations"
        )

        # Get functions
        functions = registry.get_tool_functions("Google_Sheets")
        function_names = [f.__name__ for f in functions]

        # Check for expected functions
        expected_functions = [
            "get_sheet_values",
            "append_row", 
            "update_cell",
            "search_in_sheet",
            "create_spreadsheet",
            "get_spreadsheet_info",
            "clear_range",
            "batch_update_values",
        ]

        for expected in expected_functions:
            assert expected in function_names, f"Missing function: {expected}"

    def test_google_sheets_tool_metadata(self, registry):
        """Test Google Sheets tool has proper metadata."""
        # Register tools first
        registry.register_tools_from_package(
            "shared.voice_agents.tools.implementations"
        )

        # Get Google Sheets tool class
        sheets_class = registry.get_tool_class("Google_Sheets")
        assert sheets_class is not None

        # Create instance and check metadata
        tool_instance = sheets_class(config={}, sensitive_config={})
        assert hasattr(tool_instance, "metadata")
        assert tool_instance.metadata is not None
        assert tool_instance.metadata.name == "Google_Sheets"
        assert "Google Sheets" in tool_instance.metadata.description
        assert tool_instance.metadata.requires_auth is True
        assert tool_instance.metadata.auth_type == "oauth2"

    def test_google_sheets_instantiation(self, registry):
        """Test Google Sheets tool can be instantiated with configs."""
        # Register tools first
        registry.register_tools_from_package(
            "shared.voice_agents.tools.implementations"
        )

        # Get Google Sheets tool class
        sheets_class = registry.get_tool_class("Google_Sheets")

        # Instantiate with config
        config = {"spreadsheet_id": "test-id", "default_range": "Sheet1!A1:B10"}
        sensitive_config = {
            "access_token": "test-token",
            "refresh_token": "test-refresh",
        }
        tool_instance = sheets_class(config=config, sensitive_config=sensitive_config)

        assert tool_instance is not None
        assert tool_instance.config.spreadsheet_id == "test-id"
        assert tool_instance.config.default_range == "Sheet1!A1:B10"
        assert tool_instance.sensitive_config.access_token == "test-token"
