"""
Shared pytest fixtures for all backend tests.

Note: Python paths are configured via test-env.sh (PYTHONPATH environment variable)
"""
import sys
import os
from pathlib import Path

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from uuid import uuid4
from datetime import datetime, timezone

@pytest.fixture
def sample_user_id():
    """Generate a sample user UUID."""
    return uuid4()

@pytest.fixture
def sample_org_id():
    """Generate a sample organization UUID."""
    return uuid4()

@pytest.fixture
def sample_user_data(sample_user_id):
    """Sample user data from Supabase."""
    return {
        "id": str(sample_user_id),
        "email": "test@example.com",
        "user_metadata": {
            "first_name": "Test",
            "last_name": "User"
        },
        "email_confirmed_at": datetime.now(timezone.utc).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

@pytest.fixture
def sample_organization_data(sample_org_id):
    """Sample organization data."""
    return {
        "id": str(sample_org_id),
        "name": "Test Organization",
        "description": "A test organization",
        "slug": "test-org",
        "website": "https://example.com",
        "is_active": True,
        "business_details": {"industry": "Technology"},
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

@pytest.fixture
def mock_supabase_client():
    """Create a mocked Supabase client.

    This fixture creates a fresh mock for each test and ensures
    proper cleanup to prevent state leakage between tests.
    """
    client = MagicMock()
    table_mock = MagicMock()
    table_mock.select.return_value = table_mock
    table_mock.insert.return_value = table_mock
    table_mock.update.return_value = table_mock
    table_mock.delete.return_value = table_mock
    table_mock.eq.return_value = table_mock
    table_mock.order.return_value = table_mock
    table_mock.limit.return_value = table_mock
    table_mock.single.return_value = table_mock
    table_mock.not_.return_value = table_mock
    table_mock.gte.return_value = table_mock
    table_mock.lte.return_value = table_mock
    table_mock.is_.return_value = table_mock
    table_mock.execute.return_value = MagicMock(data=[])
    client.table.return_value = table_mock

    yield client

    # Cleanup: reset mock after each test
    table_mock.reset_mock()
    client.reset_mock()

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
def mock_stripe_service():
    """Create a mocked Stripe service."""
    service = MagicMock()
    service.create_customer = AsyncMock()
    service.create_subscription = AsyncMock()
    service.cancel_subscription = AsyncMock()
    return service

@pytest.fixture
def mock_resend():
    """Create a mocked Resend email service."""
    with patch('resend.Emails.send') as mock:
        mock.return_value = {"id": "test-email-id"}
        yield mock
