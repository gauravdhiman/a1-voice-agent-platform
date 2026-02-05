"""Pytest configuration and fixtures for worker tests."""
import os
import sys
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

# Add parent directories to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))  # Project root for shared.*
sys.path.insert(0, str(project_root / "worker" / "src"))  # For worker.*

# Mock environment variables before any imports
os.environ["GEMINI_API_KEY"] = "test-gemini-key"
os.environ["LIVEKIT_URL"] = "wss://test.livekit.cloud"
os.environ["LIVEKIT_API_KEY"] = "test-api-key"
os.environ["LIVEKIT_API_SECRET"] = "test-api-secret"
os.environ["DATABASE_URL"] = "postgresql://test:test@localhost:5432/test"
os.environ["DEBUG"] = "false"


@pytest.fixture
def mock_run_context():
    """Mock LiveKit RunContext."""
    context = AsyncMock()
    return context


@pytest.fixture
def mock_job_context():
    """Mock LiveKit JobContext."""
    context = AsyncMock()
    context.room = AsyncMock()
    context.room.name = "call_+1234567890_abc123"
    context.room.remote_participants = {}
    context.connect = AsyncMock()
    context.room.on = Mock()
    return context


@pytest.fixture
def mock_agent_session():
    """Mock LiveKit AgentSession."""
    session = AsyncMock()
    session.start = AsyncMock()
    session.generate_reply = AsyncMock()
    session.shutdown = AsyncMock()
    return session


@pytest.fixture
def mock_supabase_client():
    """Mock Supabase client."""
    client = MagicMock()

    # Mock table() chain
    mock_table = MagicMock()
    mock_select = MagicMock()
    mock_insert = MagicMock()
    mock_update = MagicMock()
    mock_delete = MagicMock()
    mock_execute = MagicMock()

    mock_table.select = MagicMock(return_value=mock_select)
    mock_table.insert = MagicMock(return_value=mock_insert)
    mock_table.update = MagicMock(return_value=mock_update)
    mock_table.delete = MagicMock(return_value=mock_delete)

    mock_select.execute = MagicMock(return_value=mock_execute)
    mock_insert.execute = MagicMock(return_value=mock_execute)
    mock_update.execute = MagicMock(return_value=mock_execute)
    mock_delete.execute = MagicMock(return_value=mock_execute)

    client.table = MagicMock(return_value=mock_table)

    return client


@pytest.fixture
def sample_voice_agent():
    """Sample voice agent data."""
    return {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "name": "Test Agent",
        "phone_number": "+1234567890",
        "organization_id": "org-123",
        "persona": "Helpful Assistant",
        "tone": "Professional",
        "mission": "Assist users effectively",
        "is_active": True,
        "created_at": "2024-01-01T00:00:00",
        "updated_at": "2024-01-01T00:00:00",
    }


@pytest.fixture
def sample_agent_tool():
    """Sample agent tool data."""
    return {
        "id": "tool-123",
        "agent_id": "123e4567-e89b-12d3-a456-426614174000",
        "tool_id": "456e7890-e89b-12d3-a456-426614174000",
        "tool": {
            "id": "456e7890-e89b-12d3-a456-426614174000",
            "name": "Google_calendar",
            "description": "Google Calendar integration",
            "requires_auth": True,
            "auth_type": "oauth2",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
        },
        "config": {"calendar_id": "primary"},
        "sensitive_config": {
            "access_token": "test-access-token",
            "refresh_token": "test-refresh-token",
            "expires_at": 1234567890.0,
        },
        "is_enabled": True,
        "unselected_functions": [],
    }


@pytest.fixture
def sample_calendar_tool():
    """Sample Google Calendar tool."""
    from shared.voice_agents.tools.implementations.google_calendar import (
        GoogleCalendarTool,
    )

    return GoogleCalendarTool(
        config={"calendar_id": "primary"}, sensitive_config={}
    )


@pytest.fixture
def sample_gmail_tool():
    """Sample Gmail tool."""
    from shared.voice_agents.tools.implementations.gmail import GmailTool

    return GmailTool(
        config={"max_results": 10}, sensitive_config={}
    )
