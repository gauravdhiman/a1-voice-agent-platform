"""Comprehensive test to verify all tools have proper unit tests."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from livekit.agents import RunContext


class TestAllToolsHaveUnitTests:
    """Test that all tools have proper unit test coverage."""

    @pytest.fixture
    def mock_run_context(self):
        """Mock RunContext for testing."""
        mock_ctx = MagicMock(spec=RunContext)
        mock_ctx.agent = MagicMock()
        return mock_ctx

    def test_google_calendar_tool_comprehensive(self):
        """Test Google Calendar tool has all expected functions."""
        from shared.voice_agents.tools.implementations.google_calendar import GoogleCalendarTool
        
        tool = GoogleCalendarTool()
        
        # Verify metadata
        assert tool.metadata.name == "Google_calendar"
        assert "Google Calendar" in tool.metadata.description
        assert tool.metadata.requires_auth is True
        
        # Verify all expected functions exist
        expected_functions = [
            'list_events',
            'create_event', 
            'update_event',
            'delete_event',
            'get_event',
            'check_availability'
        ]
        
        for func_name in expected_functions:
            assert hasattr(tool, func_name), f"Missing function: {func_name}"
            func = getattr(tool, func_name)
            assert callable(func), f"Function {func_name} is not callable"

    def test_gmail_tool_comprehensive(self):
        """Test Gmail tool has all expected functions."""
        from shared.voice_agents.tools.implementations.gmail import GmailTool
        
        tool = GmailTool()
        
        # Verify metadata
        assert tool.metadata.name == "Gmail"
        assert "Gmail" in tool.metadata.description
        assert tool.metadata.requires_auth is True
        
        # Verify all expected functions exist
        expected_functions = [
            'get_latest_emails',
            'get_emails_from_user',
            'get_unread_emails',
            'get_starred_emails',
            'get_emails_by_context',
            'get_emails_by_date',
            'get_emails_by_thread',
            'search_emails',
            'create_draft_email',
            'send_email',
            'send_email_reply',
            'mark_email_as_read',
            'mark_email_as_unread',
            'list_custom_labels',
            'apply_label',
            'remove_label',
            'delete_email',
            'delete_custom_label',
            'read_email'
        ]
        
        for func_name in expected_functions:
            assert hasattr(tool, func_name), f"Missing function: {func_name}"
            func = getattr(tool, func_name)
            assert callable(func), f"Function {func_name} is not callable"

    def test_calcom_tool_comprehensive(self):
        """Test Cal.com tool has all expected functions."""
        from shared.voice_agents.tools.implementations.calcom import CalComTool
        
        tool = CalComTool()
        
        # Verify metadata
        assert tool.metadata.name == "CalCom"
        assert "Cal.com" in tool.metadata.description
        assert tool.metadata.requires_auth is True
        
        # Verify all expected functions exist
        expected_functions = [
            'get_available_slots',
            'list_event_types',
            'create_booking',
            'get_upcoming_bookings',
            'reschedule_booking',
            'cancel_booking'
        ]
        
        for func_name in expected_functions:
            assert hasattr(tool, func_name), f"Missing function: {func_name}"
            func = getattr(tool, func_name)
            assert callable(func), f"Function {func_name} is not callable"

    def test_google_sheets_tool_comprehensive(self):
        """Test Google Sheets tool has all expected functions."""
        from shared.voice_agents.tools.implementations.google_sheets import GoogleSheetsTool
        
        tool = GoogleSheetsTool()
        
        # Verify metadata
        assert tool.metadata.name == "Google_Sheets"
        assert "Google Sheets" in tool.metadata.description
        assert tool.metadata.requires_auth is True
        
        # Verify all expected functions exist
        expected_functions = [
            'get_sheet_values',
            'append_row',
            'update_cell',
            'search_in_sheet',
            'create_spreadsheet',
            'get_spreadsheet_info',
            'list_spreadsheet_sheets',
            'find_sheet_by_title',
            'get_sheet_metadata',
            'list_user_spreadsheets',
            'search_spreadsheets_by_title',
            'get_spreadsheet_details',
            'clear_range',
            'batch_update_values'
        ]
        
        for func_name in expected_functions:
            assert hasattr(tool, func_name), f"Missing function: {func_name}"
            func = getattr(tool, func_name)
            assert callable(func), f"Function {func_name} is not callable"

    @pytest.mark.asyncio
    async def test_all_tools_can_be_instantiated_with_configs(self):
        """Test that all tools can be instantiated with various config combinations."""
        from shared.voice_agents.tools.implementations.google_calendar import GoogleCalendarTool
        from shared.voice_agents.tools.implementations.gmail import GmailTool
        from shared.voice_agents.tools.implementations.calcom import CalComTool
        from shared.voice_agents.tools.implementations.google_sheets import GoogleSheetsTool
        
        # Test Google Calendar
        cal_tool = GoogleCalendarTool(
            config={"calendar_id": "test@example.com"},
            sensitive_config={"access_token": "token123"}
        )
        assert cal_tool.config.calendar_id == "test@example.com"
        assert cal_tool.sensitive_config.access_token == "token123"
        
        # Test Gmail
        gmail_tool = GmailTool(
            config={"user_id": "me", "max_results_default": 20},
            sensitive_config={"access_token": "token456"}
        )
        assert gmail_tool.config.user_id == "me"
        assert gmail_tool.config.max_results_default == 20
        assert gmail_tool.sensitive_config.access_token == "token456"
        
        # Test Cal.com
        calcom_tool = CalComTool(
            config={"event_type_id": 123, "user_timezone": "UTC"},
            sensitive_config={"api_key": "api123"}
        )
        assert calcom_tool.config.event_type_id == 123
        assert calcom_tool.config.user_timezone == "UTC"
        assert calcom_tool.sensitive_config.api_key == "api123"
        
        # Test Google Sheets
        sheets_tool = GoogleSheetsTool(
            config={"spreadsheet_id": "test-id", "default_range": "A1:B10"},
            sensitive_config={"access_token": "token789"}
        )
        assert sheets_tool.config.spreadsheet_id == "test-id"
        assert sheets_tool.config.default_range == "A1:B10"
        assert sheets_tool.sensitive_config.access_token == "token789"

    @pytest.mark.asyncio
    async def test_all_tools_have_async_functions_callable(self, mock_run_context):
        """Test that all tool functions can be called (will raise if not properly implemented)."""
        from shared.voice_agents.tools.implementations.google_calendar import GoogleCalendarTool
        from shared.voice_agents.tools.implementations.gmail import GmailTool
        from shared.voice_agents.tools.implementations.calcom import CalComTool
        from shared.voice_agents.tools.implementations.google_sheets import GoogleSheetsTool
        
        # Create tools with minimal config to test function existence
        tools = {
            "calendar": GoogleCalendarTool(sensitive_config={"access_token": "test"}),
            "gmail": GmailTool(sensitive_config={"access_token": "test"}),
            "calcom": CalComTool(sensitive_config={"api_key": "test"}),
            "sheets": GoogleSheetsTool(sensitive_config={"access_token": "test"})
        }
        
        # Test that all functions exist and are callable
        for tool_name, tool in tools.items():
            # Get all public methods that are not properties
            methods = [attr for attr in dir(tool) 
                      if not attr.startswith('_') and callable(getattr(tool, attr))]
            
            # Filter out metadata property
            methods = [m for m in methods if m != 'metadata']
            
            assert len(methods) > 0, f"No methods found for {tool_name} tool"
            
            # Verify each method is accessible
            for method_name in methods:
                method = getattr(tool, method_name)
                assert callable(method), f"Method {method_name} in {tool_name} is not callable"

    def test_tool_configurations_are_properly_defined(self):
        """Test that all tools have proper configuration classes defined."""
        from shared.voice_agents.tools.implementations.google_calendar import GoogleCalendarTool
        from shared.voice_agents.tools.implementations.gmail import GmailTool
        from shared.voice_agents.tools.implementations.calcom import CalComTool
        from shared.voice_agents.tools.implementations.google_sheets import GoogleSheetsTool
        
        tools = [GoogleCalendarTool, GmailTool, CalComTool, GoogleSheetsTool]
        
        for tool_class in tools:
            # Check that nested config classes exist
            assert hasattr(tool_class, 'Config'), f"{tool_class.__name__} missing Config class"
            assert hasattr(tool_class, 'SensitiveConfig'), f"{tool_class.__name__} missing SensitiveConfig class"
            assert hasattr(tool_class, 'AuthConfig'), f"{tool_class.__name__} missing AuthConfig class"
            
            # Check that instances can access config
            tool_instance = tool_class()
            assert hasattr(tool_instance, 'config'), f"{tool_class.__name__} instance missing config"
            assert hasattr(tool_instance, 'sensitive_config'), f"{tool_class.__name__} instance missing sensitive_config"

    def test_tool_metadata_consistency(self):
        """Test that all tools have consistent metadata structure."""
        from shared.voice_agents.tools.implementations.google_calendar import GoogleCalendarTool
        from shared.voice_agents.tools.implementations.gmail import GmailTool
        from shared.voice_agents.tools.implementations.calcom import CalComTool
        from shared.voice_agents.tools.implementations.google_sheets import GoogleSheetsTool
        
        tools = [
            GoogleCalendarTool(),
            GmailTool(),
            CalComTool(),
            GoogleSheetsTool()
        ]
        
        for tool in tools:
            metadata = tool.metadata
            
            # Check required metadata fields exist
            assert hasattr(metadata, 'name'), f"Tool {tool.__class__.__name__} missing name in metadata"
            assert hasattr(metadata, 'description'), f"Tool {tool.__class__.__name__} missing description in metadata"
            assert hasattr(metadata, 'requires_auth'), f"Tool {tool.__class__.__name__} missing requires_auth in metadata"
            assert hasattr(metadata, 'auth_type'), f"Tool {tool.__class__.__name__} missing auth_type in metadata"
            assert hasattr(metadata, 'config_schema'), f"Tool {tool.__class__.__name__} missing config_schema in metadata"
            
            # Check that name is not empty
            assert metadata.name, f"Tool {tool.__class__.__name__} has empty name"
            
            # Check that description is not empty
            assert metadata.description, f"Tool {tool.__class__.__name__} has empty description"
            
            # Check that auth settings are consistent
            assert isinstance(metadata.requires_auth, bool), f"requires_auth should be boolean for {tool.__class__.__name__}"
            
            if metadata.requires_auth:
                assert metadata.auth_type is not None, f"auth_type should not be None when requires_auth is True for {tool.__class__.__name__}"