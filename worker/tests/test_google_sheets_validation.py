"""Tests for Google Sheets tool functionality focusing on validation and structure."""

import pytest
from unittest.mock import MagicMock
from livekit.agents import RunContext


class TestGoogleSheetsToolValidation:
    """Validation tests for Google Sheets tool methods focusing on error handling and structure."""

    @pytest.fixture
    def mock_run_context(self):
        """Mock RunContext for testing."""
        mock_ctx = MagicMock(spec=RunContext)
        mock_ctx.agent = MagicMock()
        return mock_ctx

    @pytest.fixture
    def sheets_tool(self):
        """Create a Google Sheets tool instance with mock config."""
        from shared.voice_agents.tools.implementations.google_sheets import GoogleSheetsTool
        
        tool = GoogleSheetsTool(
            config={
                "spreadsheet_id": "test-spreadsheet-id",
                "default_range": "Sheet1!A1:Z1000"
            },
            sensitive_config={
                "access_token": "test-access-token",
                "refresh_token": "test-refresh-token"
            }
        )
        return tool

    @pytest.mark.asyncio
    async def test_get_sheet_values_no_access_token(self):
        """Test get_sheet_values raises error when no access token."""
        from shared.voice_agents.tools.implementations.google_sheets import GoogleSheetsTool
        
        tool = GoogleSheetsTool(
            config={"spreadsheet_id": "test-id"},
            sensitive_config={}  # No access token
        )

        with pytest.raises(ValueError, match="No access token found in sensitive config"):
            await tool.get_sheet_values(None, "test-id", "Sheet1!A1:B10")

    @pytest.mark.asyncio
    async def test_append_row_no_access_token(self):
        """Test append_row raises error when no access token."""
        from shared.voice_agents.tools.implementations.google_sheets import GoogleSheetsTool
        
        tool = GoogleSheetsTool(
            config={"spreadsheet_id": "test-id"},
            sensitive_config={}  # No access token
        )

        with pytest.raises(ValueError, match="No access token found in sensitive config"):
            await tool.append_row(None, "test-id", "Sheet1!A1", ["value"])

    @pytest.mark.asyncio
    async def test_update_cell_no_access_token(self):
        """Test update_cell raises error when no access token."""
        from shared.voice_agents.tools.implementations.google_sheets import GoogleSheetsTool
        
        tool = GoogleSheetsTool(
            config={"spreadsheet_id": "test-id"},
            sensitive_config={}  # No access token
        )

        with pytest.raises(ValueError, match="No access token found in sensitive config"):
            await tool.update_cell(None, "test-id", "Sheet1!A1", [["value"]])

    @pytest.mark.asyncio
    async def test_create_spreadsheet_no_access_token(self):
        """Test create_spreadsheet raises error when no access token."""
        from shared.voice_agents.tools.implementations.google_sheets import GoogleSheetsTool
        
        tool = GoogleSheetsTool(
            config={"spreadsheet_id": "test-id"},
            sensitive_config={}  # No access token
        )

        with pytest.raises(ValueError, match="No access token found in sensitive config"):
            await tool.create_spreadsheet(None, "Test Spreadsheet")

    @pytest.mark.asyncio
    async def test_get_spreadsheet_info_no_access_token(self):
        """Test get_spreadsheet_info raises error when no access token."""
        from shared.voice_agents.tools.implementations.google_sheets import GoogleSheetsTool
        
        tool = GoogleSheetsTool(
            config={"spreadsheet_id": "test-id"},
            sensitive_config={}  # No access token
        )

        with pytest.raises(ValueError, match="No access token found in sensitive config"):
            await tool.get_spreadsheet_info(None, "test-id")

    @pytest.mark.asyncio
    async def test_clear_range_no_access_token(self):
        """Test clear_range raises error when no access token."""
        from shared.voice_agents.tools.implementations.google_sheets import GoogleSheetsTool
        
        tool = GoogleSheetsTool(
            config={"spreadsheet_id": "test-id"},
            sensitive_config={}  # No access token
        )

        with pytest.raises(ValueError, match="No access token found in sensitive config"):
            await tool.clear_range(None, "test-id", "Sheet1!A1:B10")

    @pytest.mark.asyncio
    async def test_batch_update_values_no_access_token(self):
        """Test batch_update_values raises error when no access token."""
        from shared.voice_agents.tools.implementations.google_sheets import GoogleSheetsTool
        
        tool = GoogleSheetsTool(
            config={"spreadsheet_id": "test-id"},
            sensitive_config={}  # No access token
        )

        with pytest.raises(ValueError, match="No access token found in sensitive config"):
            await tool.batch_update_values(None, "test-id", [])

    @pytest.mark.asyncio
    async def test_search_in_sheet_no_access_token(self):
        """Test search_in_sheet raises error when no access token."""
        from shared.voice_agents.tools.implementations.google_sheets import GoogleSheetsTool
        
        tool = GoogleSheetsTool(
            config={"spreadsheet_id": "test-id"},
            sensitive_config={}  # No access token
        )

        with pytest.raises(ValueError, match="No access token found in sensitive config"):
            await tool.search_in_sheet(None, "test-id", "search-term")

    def test_tool_has_correct_structure(self, sheets_tool):
        """Test that the tool has the correct structure and methods."""
        # Verify all expected methods exist
        expected_methods = [
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

        for method_name in expected_methods:
            assert hasattr(sheets_tool, method_name), f"Missing method: {method_name}"
            method = getattr(sheets_tool, method_name)
            assert callable(method), f"Method {method_name} is not callable"

    def test_tool_config_properties(self, sheets_tool):
        """Test that the tool has correct configuration properties."""
        assert hasattr(sheets_tool, 'config')
        assert hasattr(sheets_tool, 'sensitive_config')
        assert hasattr(sheets_tool.config, 'spreadsheet_id')
        assert hasattr(sheets_tool.config, 'default_range')
        assert sheets_tool.config.spreadsheet_id == "test-spreadsheet-id"
        assert sheets_tool.config.default_range == "Sheet1!A1:Z1000"
        assert sheets_tool.sensitive_config.access_token == "test-access-token"

    @pytest.mark.asyncio
    async def test_method_signatures_match_expected(self, sheets_tool):
        """Test that method signatures match expected parameters."""
        import inspect
        
        # Test get_sheet_values signature
        get_sheet_values_sig = inspect.signature(sheets_tool.get_sheet_values)
        params = list(get_sheet_values_sig.parameters.keys())
        assert 'context' in params
        assert 'spreadsheet_id' in params
        assert 'range' in params
        
        # Test append_row signature
        append_row_sig = inspect.signature(sheets_tool.append_row)
        params = list(append_row_sig.parameters.keys())
        assert 'context' in params
        assert 'spreadsheet_id' in params
        assert 'range' in params
        assert 'values' in params
        
        # Test update_cell signature
        update_cell_sig = inspect.signature(sheets_tool.update_cell)
        params = list(update_cell_sig.parameters.keys())
        assert 'context' in params
        assert 'spreadsheet_id' in params
        assert 'range' in params
        assert 'values' in params

    def test_tool_metadata_validation(self, sheets_tool):
        """Test that the tool has correct metadata."""
        metadata = sheets_tool.metadata
        assert metadata.name == "Google_Sheets"
        assert "Google Sheets" in metadata.description
        assert metadata.requires_auth is True
        assert metadata.auth_type == "oauth2"
        assert metadata.config_schema is not None

    @pytest.mark.asyncio
    async def test_all_methods_exist_and_callable(self, sheets_tool):
        """Test that all methods exist and are callable."""
        methods_to_test = [
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
        
        for method_name in methods_to_test:
            method = getattr(sheets_tool, method_name)
            assert callable(method), f"Method {method_name} should be callable"
            
            # Test that we can get the signature without errors
            import inspect
            sig = inspect.signature(method)
            assert sig is not None, f"Could not get signature for {method_name}"