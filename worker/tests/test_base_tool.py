"""Tests for BaseTool class."""
import pytest
from shared.voice_agents.tools.base.base_tool import (
    BaseTool,
    BaseConfig,
    BaseSensitiveConfig,
    ToolMetadata,
)


class DummyTool(BaseTool):
    """Dummy tool for testing."""

    class Config(BaseConfig):
        dummy_param: str = "default_value"

    class SensitiveConfig(BaseSensitiveConfig):
        api_key: str = ""

    @property
    def metadata(self) -> ToolMetadata:
        """Tool metadata."""
        return ToolMetadata(
            name="DummyTool",
            description="A dummy tool for testing",
            config_schema={},
            requires_auth=False,
            auth_type=None,
        )

    async def dummy_action(self, context, param1: str, param2: int = 42):
        """A dummy action."""
        return {"param1": param1, "param2": param2}


class TestBaseTool:
    """Test cases for BaseTool class."""

    @pytest.fixture
    def dummy_tool(self):
        """Create a dummy tool instance."""
        return DummyTool(config={}, sensitive_config={})

    def test_initialization_with_empty_config(self, dummy_tool):
        """Test tool initialization with empty config."""
        assert dummy_tool is not None
        assert dummy_tool.config.dummy_param == "default_value"
        assert dummy_tool.sensitive_config.api_key == ""

    def test_initialization_with_config(self):
        """Test tool initialization with config."""
        config = {"dummy_param": "custom_value"}
        tool = DummyTool(config=config, sensitive_config={})

        assert tool.config.dummy_param == "custom_value"

    def test_initialization_with_sensitive_config(self):
        """Test tool initialization with sensitive config."""
        sensitive_config = {"api_key": "secret-key"}
        tool = DummyTool(config={}, sensitive_config=sensitive_config)

        assert tool.sensitive_config.api_key == "secret-key"

    def test_initialization_with_both_configs(self):
        """Test tool initialization with both configs."""
        config = {"dummy_param": "custom_value"}
        sensitive_config = {"api_key": "secret-key"}
        tool = DummyTool(config=config, sensitive_config=sensitive_config)

        assert tool.config.dummy_param == "custom_value"
        assert tool.sensitive_config.api_key == "secret-key"

    def test_metadata_property(self, dummy_tool):
        """Test metadata property."""
        metadata = dummy_tool.metadata
        assert metadata is not None
        assert metadata.name == "DummyTool"
        assert metadata.description == "A dummy tool for testing"
        assert metadata.requires_auth is False
        assert metadata.auth_type is None

    def test_config_is_immutable(self, dummy_tool):
        """Test config is Pydantic model (immutable)."""
        assert hasattr(dummy_tool.config, "model_dump")

    def test_sensitive_config_is_immutable(self, dummy_tool):
        """Test sensitive config is Pydantic model (immutable)."""
        assert hasattr(dummy_tool.sensitive_config, "model_dump")

    @pytest.mark.asyncio
    async def test_async_method_exists(self, dummy_tool, mock_run_context):
        """Test async method can be called."""
        result = await dummy_tool.dummy_action(mock_run_context, "test_value", 10)
        assert result == {"param1": "test_value", "param2": 10}

    @pytest.mark.asyncio
    async def test_async_method_with_defaults(self, dummy_tool, mock_run_context):
        """Test async method with default values."""
        result = await dummy_tool.dummy_action(mock_run_context, "test_value")
        assert result == {"param1": "test_value", "param2": 42}

    def test_base_config_is_pydantic(self):
        """Test BaseConfig is a Pydantic model."""
        assert hasattr(BaseConfig, "model_validate")

    def test_sensitive_config_is_pydantic(self):
        """Test BaseSensitiveConfig is a Pydantic model."""
        assert hasattr(BaseSensitiveConfig, "model_validate")

    def test_tool_inherits_from_base_tool(self, dummy_tool):
        """Test tool inherits from BaseTool."""
        assert isinstance(dummy_tool, BaseTool)

    def test_tool_has_required_methods(self, dummy_tool):
        """Test tool has required methods."""
        assert hasattr(dummy_tool, "metadata")
        assert hasattr(dummy_tool, "dummy_action")

    def test_tool_config_defaults(self, dummy_tool):
        """Test tool config has default values."""
        assert dummy_tool.config.dummy_param == "default_value"

    def test_tool_sensitive_config_defaults(self, dummy_tool):
        """Test tool sensitive config has default values."""
        assert dummy_tool.sensitive_config.api_key == ""

    def test_multiple_tool_instances(self):
        """Test multiple tool instances are independent."""
        tool1 = DummyTool(
            config={"dummy_param": "value1"}, sensitive_config={"api_key": "key1"}
        )
        tool2 = DummyTool(
            config={"dummy_param": "value2"}, sensitive_config={"api_key": "key2"}
        )

        assert tool1.config.dummy_param == "value1"
        assert tool2.config.dummy_param == "value2"
        assert tool1.sensitive_config.api_key == "key1"
        assert tool2.sensitive_config.api_key == "key2"


class TestGoogleCalendarTool:
    """Test cases for GoogleCalendarTool."""

    @pytest.fixture
    def calendar_tool(self):
        """Create a Google Calendar tool instance."""
        from shared.voice_agents.tools.implementations.google_calendar import (
            GoogleCalendarTool,
        )

        return GoogleCalendarTool(config={}, sensitive_config={})

    def test_calendar_tool_initialization(self, calendar_tool):
        """Test Google Calendar tool initialization."""
        assert calendar_tool is not None
        assert calendar_tool.config.calendar_id == "primary"

    def test_calendar_tool_metadata(self, calendar_tool):
        """Test Google Calendar tool metadata."""
        metadata = calendar_tool.metadata
        assert metadata is not None
        assert metadata.name == "Google_calendar"
        assert "Google Calendar" in metadata.description
        assert metadata.requires_auth is True
        assert metadata.auth_type == "oauth2"

    def test_calendar_tool_has_required_functions(self, calendar_tool):
        """Test Google Calendar tool has required functions."""
        required_functions = [
            "check_availability",
            "create_event",
            "update_event",
            "delete_event",
            "list_events",
            "get_event",
        ]

        for func_name in required_functions:
            assert hasattr(
                calendar_tool, func_name
            ), f"Missing function: {func_name}"

    def test_calendar_tool_config(self, calendar_tool):
        """Test Google Calendar tool config."""
        assert hasattr(calendar_tool.config, "calendar_id")
        assert calendar_tool.config.calendar_id == "primary"

    @pytest.mark.asyncio
    async def test_calendar_tool_check_availability_exists(
        self, calendar_tool, mock_run_context
    ):
        """Test check_availability method exists and is async."""
        assert hasattr(calendar_tool, "check_availability")
        assert callable(calendar_tool.check_availability)


class TestGmailTool:
    """Test cases for GmailTool."""

    @pytest.fixture
    def gmail_tool(self):
        """Create a Gmail tool instance."""
        from shared.voice_agents.tools.implementations.gmail import GmailTool

        return GmailTool(config={}, sensitive_config={})

    def test_gmail_tool_initialization(self, gmail_tool):
        """Test Gmail tool initialization."""
        assert gmail_tool is not None
        assert gmail_tool.config.max_results_default == 10

    def test_gmail_tool_metadata(self, gmail_tool):
        """Test Gmail tool metadata."""
        metadata = gmail_tool.metadata
        assert metadata is not None
        assert metadata.name == "Gmail"
        assert "Gmail" in metadata.description
        assert metadata.requires_auth is True
        assert metadata.auth_type == "oauth2"

    def test_gmail_tool_has_required_functions(self, gmail_tool):
        """Test Gmail tool has core functions."""
        required_functions = [
            "send_email",
            "read_email",
            "search_emails",
            "delete_email",
        ]

        for func_name in required_functions:
            assert hasattr(
                gmail_tool, func_name
            ), f"Missing function: {func_name}"

    def test_gmail_tool_config(self, gmail_tool):
        """Test Gmail tool config."""
        assert hasattr(gmail_tool.config, "max_results_default")
        assert gmail_tool.config.max_results_default == 10

    @pytest.mark.asyncio
    async def test_gmail_tool_send_email_exists(
        self, gmail_tool, mock_run_context
    ):
        """Test send_email method exists and is async."""
        assert hasattr(gmail_tool, "send_email")
        assert callable(gmail_tool.send_email)


class TestGoogleSheetsTool:
    """Test cases for GoogleSheetsTool."""

    @pytest.fixture
    def sheets_tool(self):
        """Create a Google Sheets tool instance."""
        from shared.voice_agents.tools.implementations.google_sheets import GoogleSheetsTool

        return GoogleSheetsTool(config={}, sensitive_config={})

    def test_sheets_tool_initialization(self, sheets_tool):
        """Test Google Sheets tool initialization."""
        assert sheets_tool is not None
        assert sheets_tool.config.spreadsheet_id == ""
        assert sheets_tool.config.default_range == "Sheet1!A1:Z1000"

    def test_sheets_tool_metadata(self, sheets_tool):
        """Test Google Sheets tool metadata."""
        metadata = sheets_tool.metadata
        assert metadata is not None
        assert metadata.name == "Google_Sheets"
        assert "Google Sheets" in metadata.description
        assert metadata.requires_auth is True
        assert metadata.auth_type == "oauth2"

    def test_sheets_tool_has_all_functions(self, sheets_tool):
        """Test Google Sheets tool has all required functions."""
        required_functions = [
            "get_sheet_values",
            "append_row",
            "update_cell",
            "search_in_sheet",
            "create_spreadsheet",
            "get_spreadsheet_info",
            "list_spreadsheet_sheets",
            "find_sheet_by_title",
            "get_sheet_metadata",
            "list_user_spreadsheets",
            "search_spreadsheets_by_title",
            "get_spreadsheet_details",
            "clear_range",
            "batch_update_values",
        ]

        for func_name in required_functions:
            assert hasattr(
                sheets_tool, func_name
            ), f"Missing function: {func_name}"

    def test_sheets_tool_config(self, sheets_tool):
        """Test Google Sheets tool config."""
        assert hasattr(sheets_tool.config, "spreadsheet_id")
        assert hasattr(sheets_tool.config, "default_range")
        assert sheets_tool.config.spreadsheet_id == ""
        assert sheets_tool.config.default_range == "Sheet1!A1:Z1000"

    @pytest.mark.asyncio
    async def test_get_sheet_values_exists(self, sheets_tool, mock_run_context):
        """Test get_sheet_values method exists and is async."""
        assert hasattr(sheets_tool, "get_sheet_values")
        assert callable(sheets_tool.get_sheet_values)

    @pytest.mark.asyncio
    async def test_append_row_exists(self, sheets_tool, mock_run_context):
        """Test append_row method exists and is async."""
        assert hasattr(sheets_tool, "append_row")
        assert callable(sheets_tool.append_row)

    @pytest.mark.asyncio
    async def test_update_cell_exists(self, sheets_tool, mock_run_context):
        """Test update_cell method exists and is async."""
        assert hasattr(sheets_tool, "update_cell")
        assert callable(sheets_tool.update_cell)

    @pytest.mark.asyncio
    async def test_search_in_sheet_exists(self, sheets_tool, mock_run_context):
        """Test search_in_sheet method exists and is async."""
        assert hasattr(sheets_tool, "search_in_sheet")
        assert callable(sheets_tool.search_in_sheet)

    @pytest.mark.asyncio
    async def test_create_spreadsheet_exists(self, sheets_tool, mock_run_context):
        """Test create_spreadsheet method exists and is async."""
        assert hasattr(sheets_tool, "create_spreadsheet")
        assert callable(sheets_tool.create_spreadsheet)

    @pytest.mark.asyncio
    async def test_get_spreadsheet_info_exists(self, sheets_tool, mock_run_context):
        """Test get_spreadsheet_info method exists and is async."""
        assert hasattr(sheets_tool, "get_spreadsheet_info")
        assert callable(sheets_tool.get_spreadsheet_info)

    @pytest.mark.asyncio
    async def test_clear_range_exists(self, sheets_tool, mock_run_context):
        """Test clear_range method exists and is async."""
        assert hasattr(sheets_tool, "clear_range")
        assert callable(sheets_tool.clear_range)

    @pytest.mark.asyncio
    async def test_batch_update_values_exists(self, sheets_tool, mock_run_context):
        """Test batch_update_values method exists and is async."""
        assert hasattr(sheets_tool, "batch_update_values")
        assert callable(sheets_tool.batch_update_values)

    @pytest.mark.asyncio
    async def test_list_spreadsheet_sheets_exists(self, sheets_tool, mock_run_context):
        """Test list_spreadsheet_sheets method exists and is async."""
        assert hasattr(sheets_tool, "list_spreadsheet_sheets")
        assert callable(sheets_tool.list_spreadsheet_sheets)

    @pytest.mark.asyncio
    async def test_find_sheet_by_title_exists(self, sheets_tool, mock_run_context):
        """Test find_sheet_by_title method exists and is async."""
        assert hasattr(sheets_tool, "find_sheet_by_title")
        assert callable(sheets_tool.find_sheet_by_title)

    @pytest.mark.asyncio
    async def test_get_sheet_metadata_exists(self, sheets_tool, mock_run_context):
        """Test get_sheet_metadata method exists and is async."""
        assert hasattr(sheets_tool, "get_sheet_metadata")
        assert callable(sheets_tool.get_sheet_metadata)

    @pytest.mark.asyncio
    async def test_list_user_spreadsheets_exists(self, sheets_tool, mock_run_context):
        """Test list_user_spreadsheets method exists and is async."""
        assert hasattr(sheets_tool, "list_user_spreadsheets")
        assert callable(sheets_tool.list_user_spreadsheets)

    @pytest.mark.asyncio
    async def test_search_spreadsheets_by_title_exists(self, sheets_tool, mock_run_context):
        """Test search_spreadsheets_by_title method exists and is async."""
        assert hasattr(sheets_tool, "search_spreadsheets_by_title")
        assert callable(sheets_tool.search_spreadsheets_by_title)

    @pytest.mark.asyncio
    async def test_get_spreadsheet_details_exists(self, sheets_tool, mock_run_context):
        """Test get_spreadsheet_details method exists and is async."""
        assert hasattr(sheets_tool, "get_spreadsheet_details")
        assert callable(sheets_tool.get_spreadsheet_details)
