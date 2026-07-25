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


# ---------------------------------------------------------------------------
# MCP reference-server fixtures (Phase 1 MCP integration).
#
# Shared by tests/test_mcp_client.py and tests/test_mcp_livekit_adapter.py.
# Imports are lazy (inside the helpers) so collecting the rest of the worker
# suite does not pay the uvicorn/FastMCP import cost. The server runs in-process
# on an ephemeral localhost port over real HTTP — deterministic, no external
# network, no third-party OAuth.
# ---------------------------------------------------------------------------


def _free_tcp_port() -> int:
    """Reserve and release an ephemeral localhost port for the test server."""
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _build_calculator_server():
    """Build a small FastMCP reference server with two arithmetic tools."""
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP("calculator")

    @mcp.tool()
    def add(a: int, b: int) -> int:
        """Add two integers and return the sum."""
        return a + b

    @mcp.tool()
    def multiply(a: int, b: int) -> int:
        """Multiply two integers and return the product."""
        return a * b

    return mcp


async def _start_mcp_server(mcp_server):
    """Start a FastMCP Streamable HTTP server on an ephemeral port.

    Returns the MCP endpoint URL, the uvicorn Server, and the background task.
    """
    import asyncio

    import uvicorn

    port = _free_tcp_port()
    app = mcp_server.streamable_http_app()
    config = uvicorn.Config(
        app, host="127.0.0.1", port=port, log_level="warning", lifespan="on"
    )
    server = uvicorn.Server(config)
    task = asyncio.create_task(server.serve())
    for _ in range(200):
        if server.started:
            break
        await asyncio.sleep(0.02)
    assert server.started, "reference MCP server failed to start"
    return f"http://127.0.0.1:{port}/mcp", server, task


async def _stop_mcp_server(server, task) -> None:
    """Gracefully shut down the in-process uvicorn server."""
    import asyncio

    server.should_exit = True
    try:
        await asyncio.wait_for(task, timeout=5)
    except asyncio.TimeoutError:
        task.cancel()


@pytest.fixture
async def mcp_server_url():
    """Yield the URL of a running in-process FastMCP calculator server."""
    mcp = _build_calculator_server()
    url, server, task = await _start_mcp_server(mcp)
    try:
        yield url
    finally:
        await _stop_mcp_server(server, task)


@pytest.fixture
def mcp_server_config(mcp_server_url):
    """Build an McpServerConfig pointing at the running reference server."""
    from shared.voice_agents.tools.mcp.models import McpServerConfig

    return McpServerConfig(url=mcp_server_url, name="calculator", timeout=10.0)


# ---------------------------------------------------------------------------
# Google Calendar MCP reference server fixture (Phase 3b — first working tool).
#
# Stands up the in-memory google-calendar FastMCP server from
# shared.voice_agents.tools.mcp.reference_servers so the full platform pipeline
# (McpClient -> build_mcp_livekit_tools -> LiveKit handler) can be exercised
# against a Google-Calendar-shaped tool. Same in-process start/stop harness as
# the calculator server above.
# ---------------------------------------------------------------------------


@pytest.fixture
async def google_calendar_mcp_url():
    """Yield the URL of a running in-process Google Calendar MCP server."""
    from shared.voice_agents.tools.mcp.reference_servers import (
        build_google_calendar_server,
    )

    mcp = build_google_calendar_server()
    url, server, task = await _start_mcp_server(mcp)
    try:
        yield url
    finally:
        await _stop_mcp_server(server, task)


@pytest.fixture
def google_calendar_mcp_config(google_calendar_mcp_url):
    """Build an McpServerConfig pointing at the running Google Calendar server."""
    from shared.voice_agents.tools.mcp.models import McpServerConfig

    return McpServerConfig(
        url=google_calendar_mcp_url, name="google-calendar", timeout=10.0
    )


# ---------------------------------------------------------------------------
# Google Calendar REST connector fixture (works with a personal Gmail token,
# no Workspace Developer Preview). Stands up the REST-wrapping FastMCP server
# from shared.voice_agents.tools.mcp.reference_servers so the full platform
# pipeline can be exercised against real Google-Calendar-shaped tool calls
# with the Google HTTP layer mocked via httpx.MockTransport in each test.
# ---------------------------------------------------------------------------


@pytest.fixture
async def google_calendar_rest_mcp_url():
    """Yield the URL of a running in-process Google Calendar REST connector."""
    from shared.voice_agents.tools.mcp.reference_servers import (
        build_google_calendar_rest_server,
    )

    mcp = build_google_calendar_rest_server()
    url, server, task = await _start_mcp_server(mcp)
    try:
        yield url
    finally:
        await _stop_mcp_server(server, task)


@pytest.fixture
def google_calendar_rest_mcp_config(google_calendar_rest_mcp_url):
    """Build an McpServerConfig pointing at the running REST connector."""
    from shared.voice_agents.tools.mcp.models import McpServerConfig

    return McpServerConfig(
        url=google_calendar_rest_mcp_url,
        name="google-calendar-rest",
        timeout=10.0,
        headers={"Authorization": "Bearer test-token"},
    )
