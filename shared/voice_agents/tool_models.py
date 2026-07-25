"""
Pydantic models for Platform Tool functionality.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field

from shared.voice_agents.tools.base.auth_config import BaseAuthConfig


class AuthStatus(str, Enum):
    """Authentication status for a tool."""

    NOT_AUTHENTICATED = "not_authenticated"  # No tokens exist
    AUTHENTICATED = "authenticated"  # Valid tokens exist
    EXPIRED = "expired"  # Tokens exist but have expired


class ConnectionStatus(str, Enum):
    """Connection status for a tool."""

    NOT_CONNECTED = "not_connected"  # No agent_tools record
    CONNECTED_NO_AUTH = "connected_no_auth"  # Connected, tool doesn't require auth
    CONNECTED_AUTH_VALID = "connected_auth_valid"  # Connected, requires auth, valid tokens
    CONNECTED_AUTH_INVALID = (
        "connected_auth_invalid"
    )  # Connected, requires auth, invalid/missing tokens


class ToolSource(str, Enum):
    """Where a platform tool's implementation lives.

    Determines how the worker resolves a ``platform_tools`` row into callable
    LiveKit tools. See ``docs/03_implementation/mcp_integration_rfc.md``.

    Attributes:
        LEGACY: In-tree ``BaseTool`` subclass, resolved via the
            ``LiveKitToolRegistry`` from the tool's ``name``. This is the
            original, pre-MCP mechanism and remains the default.
        MCP: Remote MCP server reached over Streamable HTTP. The worker builds
            an :class:`~shared.voice_agents.tools.mcp.client.McpClient` from the
            row's ``mcp_server_*`` fields, discovers the server's tools, and
            synthesizes LiveKit ``RawFunctionTool`` wrappers for each. Coexists
            with ``LEGACY`` per RFC §1.1 (no teardown until proven).
    """

    LEGACY = "legacy"
    MCP = "mcp"


class PlatformToolBase(BaseModel):
    """Base model for Platform Tool."""

    name: str = Field(..., min_length=1, max_length=100, description="Tool name")
    description: Optional[str] = Field(None, description="Tool description")
    config_schema: Optional[Dict[str, Any]] = Field(
        None, description="JSON schema for tool configuration"
    )
    auth_type: Optional[str] = Field(
        None, description="Authentication type (e.g., 'oauth2', 'api_key')"
    )
    requires_auth: bool = Field(
        default=False, description="Whether tool requires authentication"
    )
    auth_config: Optional[Union[Dict[str, Any], BaseAuthConfig]] = Field(
        None, description="Authentication config (OAuth URLs, scopes, provider)"
    )
    is_active: bool = Field(
        default=True, description="Whether is tool available for use"
    )
    # --- MCP integration (Phase 2) -----------------------------------------
    # Additive, all optional/defaulted so legacy rows and pre-migration code
    # keep working: a row without these columns is treated as ``LEGACY``.
    # See ``docs/03_implementation/mcp_integration_rfc.md``.
    tool_source: ToolSource = Field(
        default=ToolSource.LEGACY,
        description=(
            "Where the tool implementation lives: 'legacy' (in-tree BaseTool "
            "via LiveKitToolRegistry) or 'mcp' (remote MCP server)."
        ),
    )
    mcp_server_url: Optional[str] = Field(
        None,
        description=(
            "Streamable HTTP endpoint of the MCP server, e.g. "
            "'https://host/mcp'. Only used when tool_source == 'mcp'."
        ),
    )
    mcp_server_headers: Optional[Dict[str, str]] = Field(
        None,
        description=(
            "Static headers sent on every MCP request (server-level auth, e.g. "
            "an API key). Per-org user OAuth tokens are injected at call time "
            "from the agent_tool sensitive_config; this field is for "
            "server-level credentials only."
        ),
    )
    mcp_server_name: Optional[str] = Field(
        None,
        description=(
            "Human-readable MCP server name used for logging/labels. Defaults "
            "to the tool name when unset. Only used when tool_source == 'mcp'."
        ),
    )


class PlatformToolCreate(PlatformToolBase):
    """Model for creating a new platform tool."""

    tool_functions_schema: Optional[Dict[str, Any]] = Field(
        None, description="Function schemas for LLM debugging and inspection"
    )


class PlatformTool(PlatformToolBase):
    """Model for a platform tool with all attributes."""

    id: UUID = Field(..., description="Tool ID")
    tool_functions_schema: Optional[Dict[str, Any]] = Field(
        None, description="Function schemas for LLM debugging and inspection"
    )
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class AgentToolBase(BaseModel):
    """Base model for Agent Tool configuration."""

    agent_id: UUID = Field(..., description="Agent ID")
    tool_id: UUID = Field(..., description="Tool ID")
    config: Optional[Dict[str, Any]] = Field(
        None, description="Public tool configuration for this agent"
    )
    sensitive_config: Optional[Dict[str, Any]] = Field(
        None,
        description=(
            "Sensitive tool config (will be encrypted), "
            "e.g., auth token, refresh token."
        ),
    )
    unselected_functions: Optional[List[str]] = Field(
        None,
        description="Function names to disable (all others enabled by default)",
    )
    is_enabled: bool = Field(
        default=True, description="Whether is tool enabled for this agent"
    )


class AgentToolCreate(AgentToolBase):
    """Model for configuring a tool for an agent."""

    pass


class AgentToolUpdate(BaseModel):
    """Model for updating an agent tool configuration."""

    config: Optional[Dict[str, Any]] = Field(
        None, description="Public tool configuration for this agent"
    )
    sensitive_config: Optional[Dict[str, Any]] = Field(
        None, description="Sensitive tool configuration (will be encrypted)"
    )
    unselected_functions: Optional[List[str]] = Field(
        None,
        description="Function names to disable (all others enabled by default)",
    )
    is_enabled: Optional[bool] = Field(
        None, description="Whether is tool enabled for this agent"
    )
    last_refreshed_at: Optional[datetime] = Field(
        None, description="Timestamp when OAuth tokens were last auto-refreshed"
    )


class AgentTool(AgentToolBase):
    """Model for an agent tool with all attributes (internal use)."""

    id: UUID = Field(..., description="Agent tool configuration ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    last_refreshed_at: Optional[datetime] = Field(
        None, description="Timestamp when OAuth tokens were last auto-refreshed"
    )
    tool: Optional[PlatformTool] = Field(None, description="Tool details")


class AgentToolResponse(BaseModel):
    """Response model for agent tool (excludes sensitive config)."""

    id: UUID = Field(..., description="Agent tool configuration ID")
    agent_id: UUID = Field(..., description="Agent ID")
    tool_id: UUID = Field(..., description="Tool ID")
    config: Optional[Dict[str, Any]] = Field(
        None, description="Public tool configuration for this agent"
    )
    unselected_functions: Optional[List[str]] = Field(
        None,
        description="Function names to disable (all others enabled by default)",
    )
    is_enabled: bool = Field(
        default=True, description="Whether is tool enabled for this agent"
    )
    auth_status: AuthStatus = Field(
        default=AuthStatus.NOT_AUTHENTICATED,
        description="Authentication status of the tool",
    )
    token_expires_at: Optional[float] = Field(
        None, description="Timestamp when access token expires (Unix timestamp)"
    )
    connection_status: ConnectionStatus = Field(
        default=ConnectionStatus.NOT_CONNECTED,
        description="Connection status of the tool",
    )
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    tool: Optional[PlatformTool] = Field(None, description="Tool details")
