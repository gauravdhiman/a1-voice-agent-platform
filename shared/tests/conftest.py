"""
Shared test configuration for all modules.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone


@pytest.fixture
def mock_supabase_client():
    """Create a mocked Supabase client."""
    client = MagicMock()
    # Setup table mock that returns chainable methods
    table_mock = MagicMock()
    table_mock.select.return_value = table_mock
    table_mock.insert.return_value = table_mock
    table_mock.update.return_value = table_mock
    table_mock.delete.return_value = table_mock
    table_mock.upsert.return_value = table_mock
    table_mock.eq.return_value = table_mock
    table_mock.match.return_value = table_mock
    table_mock.is_.return_value = table_mock
    table_mock.order.return_value = table_mock
    table_mock.execute.return_value = MagicMock(data=[])
    client.table.return_value = table_mock
    return client


@pytest.fixture
def mock_supabase_auth():
    """Create a mocked Supabase auth client."""
    auth = MagicMock()
    auth.sign_up = MagicMock()
    auth.sign_in_with_password = MagicMock()
    auth.sign_out = MagicMock()
    auth.refresh_session = MagicMock()
    auth.get_user = MagicMock()
    auth.admin = MagicMock()
    auth.admin.list_users = MagicMock()
    return auth


@pytest.fixture
def sample_user_id():
    """Generate a sample user UUID."""
    return uuid4()


@pytest.fixture
def sample_org_id():
    """Generate a sample organization UUID."""
    return uuid4()