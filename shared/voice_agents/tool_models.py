"""
Pydantic models for Platform Tool functionality.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field

from shared.voice_agents.tools.base.auth_config import BaseAuthConfig
from shared.voice_agents.tools.base.oauth_support import OAuthRefreshMode


class AuthStatus(str, Enum):
    """Authentication status for a tool."""

    NOT_AUTHENTICATED = "not_authenticated"  # No tokens exist
    AUTHENTICATED = "authenticated"  # Valid tokens exist
    EXPIRED = "expired"  # Tokens exist but have expired


class ConnectionStatus(str, Enum):
    """Connection status for a tool."""

    NOT_CONNECTED = "not_connected"  # No agent_tools record
    CONNECTED_NO_AUTH = "connected_no_auth"  # Connected, tool doesn't require auth
    CONNECTED_AUTH_VALID = (
        "connected_auth_valid"  # Connected, requires auth, valid tokens
    )
    CONNECTED_AUTH_INVALID = (
        "connected_auth_invalid"  # Connected, requires auth, invalid/missing tokens
    )
    CONFIGURATION_REQUIRED = (
        "configuration_required"  # Attached but missing required tool configuration
    )


class ToolSource(str, Enum):
    """Where a platform tool's implementation lives.

    Determines how the worker resolves a ``platform_tools`` row into callable
    Pipecat/voice-ws tools. See ``docs/03_implementation/mcp_integration_rfc.md``.

    Attributes:
        LEGACY: In-tree ``BaseTool`` subclass, resolved via the
            ``PlatformToolRegistry`` from the tool's ``name``. This is the
            original, pre-MCP mechanism and remains the default.
        MCP: Remote MCP server reached over Streamable HTTP. The worker builds
            an :class:`~shared.voice_agents.tools.mcp.client.McpClient` from the
            row's ``mcp_server_*`` fields, discovers the server's tools, and
            synthesizes Pipecat function schemas and handlers for each. Coexists
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
    is_premium: bool = Field(
        default=False,
        description=(
            "Whether the tool requires the 'premium_tools' plan feature. "
            "Premium tools are visible in the catalog with a Premium badge "
            "but cannot be attached to an agent unless the org's plan "
            "entitles the 'premium_tools' feature (gate enforced at attach "
            "time in the API layer)."
        ),
    )
    # --- MCP integration (Phase 2) -----------------------------------------
    # Additive, all optional/defaulted so legacy rows and pre-migration code
    # keep working: a row without these columns is treated as ``LEGACY``.
    # See ``docs/03_implementation/mcp_integration_rfc.md``.
    tool_source: ToolSource = Field(
        default=ToolSource.LEGACY,
        description=(
            "Where the tool implementation lives: 'legacy' (in-tree BaseTool "
            "via PlatformToolRegistry) or 'mcp' (remote MCP server)."
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
    mcp_server_secret_headers: Optional[str] = Field(
        None,
        description=(
            "Encrypted JSON of server-level secret headers (e.g. an API key). "
            "Encrypted at rest via Fernet; decrypted and merged with "
            "mcp_server_headers (public) and the per-user OAuth bearer at "
            "call time by the worker. Accept this field on create/update; "
            "never return it in plaintext (use mcp_secret_headers_configured "
            "in the response model). Only used when tool_source == 'mcp'."
        ),
    )
    # --- publish lifecycle (platform-admin authoring) ---------------------
    # Custom MCP servers are authored by platform admins, tested in-memory,
    # then PUBLISHED to the global catalog. FALSE = draft (platform-admin
    # only); TRUE = visible to all org users in the tool panel (with
    # is_active). Retires the org-scoped custom tier (organization_id below is
    # now dormant). See docs/03_implementation/mcp_integration_rfc.md §6.6.
    is_published: bool = Field(
        default=False,
        description=(
            "Publish state: False = draft (platform-admin-only), True = "
            "published to the global catalog (visible to all org users). "
            "Combined with is_active for org-user visibility. Custom MCP "
            "servers are authored + tested by platform admins then published."
        ),
    )
    # --- org scope (RETIRED — kept dormant for a future org-private tier) ---
    # Was: org-scoped custom servers created per-tenant. The publish-lifecycle
    # model replaces it: all custom servers are platform-published = global.
    # The column is retained (additive, nullable) for a possible future
    # org-private-publish tier; the org-scoped read/create code paths are
    # removed. See docs/03_implementation/mcp_integration_rfc.md §6.6.
    organization_id: Optional[UUID] = Field(
        None,
        description=(
            "DORMANT. Owning organization for a future org-private-publish "
            "tier. NULL = global (platform-published) — the only mode today. "
            "Kept for forward-compat; the org-scoped custom tier is retired."
        ),
    )


class PlatformToolCreate(PlatformToolBase):
    """Model for creating a new platform tool."""

    tool_functions_schema: Optional[Dict[str, Any]] = Field(
        None, description="Function schemas for LLM debugging and inspection"
    )
    # Plaintext secret headers from the UI, encrypted by the service into
    # mcp_server_secret_headers before persisting. ``exclude=True`` so it is
    # NEVER written to the DB as-is (the service handles encryption). Only
    # meaningful for tool_source == 'mcp' custom servers.
    mcp_secret_headers_input: Optional[Dict[str, str]] = Field(
        None,
        exclude=True,
        description=(
            "Plaintext server-level secret headers (e.g. an API key) supplied "
            "from the UI. The service encrypts these into "
            "mcp_server_secret_headers; this field is never persisted directly."
        ),
    )
    # Confidential OAuth client secrets are accepted only through this
    # write-only field. The service encrypts them into a dedicated database
    # column; they must never be embedded in the public auth_config JSONB.
    oauth_client_secret_input: Optional[str] = Field(
        None,
        exclude=True,
        description=(
            "Write-only OAuth client secret. Encrypted at rest by the service "
            "and never returned in a platform-tool response."
        ),
    )


class PlatformTool(PlatformToolBase):
    """Model for a platform tool with all attributes."""

    id: UUID = Field(..., description="Tool ID")
    tool_functions_schema: Optional[Dict[str, Any]] = Field(
        None, description="Function schemas for LLM debugging and inspection"
    )
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    # Read-only flag surfaced to the frontend so the UI can show that secret
    # headers are configured WITHOUT ever exposing the encrypted/decrypted
    # values. The raw mcp_server_secret_headers column is set on this model by
    # the service for internal (worker) use but must be stripped before the
    # response leaves the API.
    mcp_secret_headers_configured: bool = Field(
        default=False,
        description="Whether encrypted server-level secret headers are set.",
    )
    oauth_client_secret_encrypted: Optional[str] = Field(
        None,
        exclude=True,
        description="Internal encrypted OAuth client secret; never returned.",
    )
    oauth_client_secret_configured: bool = Field(
        default=False,
        description="Whether a confidential OAuth client secret is configured.",
    )
    oauth_refresh_mode: Optional[OAuthRefreshMode] = Field(
        None,
        description=("Expected OAuth refresh behavior: automatic, manual, or unknown."),
    )
    oauth_refresh_interval_minutes: Optional[int] = Field(
        None,
        description=(
            "Optional admin-declared manual reauthorization interval in minutes."
        ),
    )
    oauth_refresh_message: Optional[str] = Field(
        None,
        description="Safe OAuth refresh guidance for platform and org admins.",
    )


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
    # These fields are internal context used by background services. They are
    # deliberately not part of AgentToolResponse, which is the public API
    # model and never carries decrypted connection state.
    agent_name: Optional[str] = Field(
        None, exclude=True, description="Agent name for internal notifications"
    )
    organization_id: Optional[UUID] = Field(
        None,
        exclude=True,
        description="Owning organization for internal notifications",
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
    configuration_issues: List[str] = Field(
        default_factory=list,
        description=(
            "Missing configuration pieces blocking this attachment "
            "(empty when complete)"
        ),
    )
    last_refreshed_at: Optional[datetime] = Field(
        None,
        description="Timestamp when OAuth tokens were last auto-refreshed",
    )
    oauth_refresh_mode: Optional[OAuthRefreshMode] = Field(
        None,
        description="Actual or expected OAuth refresh behavior for this connection",
    )
    oauth_refresh_interval_minutes: Optional[int] = Field(
        None,
        description="Optional manual reauthorization interval in minutes",
    )
    oauth_refresh_message: Optional[str] = Field(
        None,
        description="Safe OAuth refresh guidance for admins",
    )
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    tool: Optional[PlatformTool] = Field(None, description="Tool details")
