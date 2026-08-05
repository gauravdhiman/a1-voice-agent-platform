"""
Tool API routes for the platform.
"""

import base64
import json
import logging
import os
from datetime import datetime
from typing import List
from urllib.parse import quote
from uuid import UUID

import httpx
from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from opentelemetry import trace
from pydantic import BaseModel, Field
from src.auth.dependencies import assert_has_permission, assert_platform_role
from src.auth.middleware import get_authenticated_user
from src.auth.models import UserProfile

from shared.voice_agents.service import voice_agent_service
from shared.voice_agents.tool_models import (
    AgentToolCreate,
    AgentToolUpdate,
    AgentToolResponse,
    PlatformTool,
    PlatformToolCreate,
    ToolSource,
)
from shared.voice_agents.tool_service import tool_service
from shared.voice_agents.tools.base.oauth_provider_utils import (
    get_oauth_manager,
)
from shared.voice_agents.tools.mcp.errors import format_mcp_client_error
from shared.voice_agents.tools.mcp.json_http_client import (
    McpJsonRpcError,
    list_tools_json_http,
)
from shared.voice_agents.tools.mcp.models import McpServerConfig
from shared.voice_agents.tools.mcp.security import (
    parse_mcp_servers_json,
    validate_mcp_server_url,
)

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)
tool_router = APIRouter(prefix="/api/v1/tools", tags=["Tools"])


# --- MCP configure-from-UI request models ---------------------------------
# Lightweight payloads for the "Add MCP server" flow. Discover and parse are
# in-memory (nothing persisted); create reuses PlatformToolCreate.
class McpDiscoverRequest(BaseModel):
    """In-memory discover request: test a remote MCP server's tools.

    Attributes:
        url: Streamable HTTP endpoint of the MCP server to probe.
        headers: Static headers (e.g. an API key) to send on the probe.
    """

    url: str
    headers: dict[str, str] = Field(default_factory=dict)


class McpParseRequest(BaseModel):
    """Raw pasted ``mcpServers`` JSON config to parse into server configs."""

    raw: str


async def _assert_agent_tool_admin(
    agent_tool_id: UUID, user_profile: UserProfile
) -> AgentToolResponse:
    """Verify the caller can administer the given agent_tool.

    Resolves ``agent_tool_id`` → ``agent_id`` → ``organization_id`` and
    enforces ``agent:update`` on that org (platform_admin short-circuits
    inside :func:`assert_has_permission`). Tool configuration is an
    agent-mutation, so it uses the same permission as agent update
    rather than a bare ``org_admin`` role check.

    All four write endpoints on the agent-tools resource (``update``,
    ``logout``, ``api-key``, ``delete``) call this before the service layer.

    Raises:
        HTTPException: 404 if missing, 403 if permission denied.
    """
    agent_tool, error = await tool_service.get_agent_tool_by_id(agent_tool_id)
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=error
        )
    if agent_tool is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent tool not found",
        )

    agent, agent_error = await voice_agent_service.get_agent_by_id(
        agent_tool.agent_id
    )
    if agent_error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=agent_error
        )
    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found"
        )

    assert_has_permission(
        user_profile,
        "agent",
        "update",
        agent.organization_id,
        error_message="Admin role required to modify this agent tool",
    )

    return agent_tool


# Platform Tools (platform-admin only for authoring/publish; org admins attach)
@tool_router.post(
    "/platform", response_model=PlatformTool, status_code=status.HTTP_201_CREATED
)
@tracer.start_as_current_span("tool.routes.create_platform_tool")
async def create_platform_tool(
    tool_data: PlatformToolCreate,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Create or update a platform tool (platform-admin authoring).

    Publish lifecycle (RFC §6.6): custom MCP servers are authored by
    **platform admins** only. A server is created as a **draft**
    (``is_published=False``) unless the payload sets ``is_published=True``
    (publish-on-create). Once published it appears in the global catalog for
    org admins to attach. The org-scoped custom tier is retired — MCP rows are
    always global (``organization_id`` forced off in the service); the
    ``organization_id`` payload field is ignored for MCP rows.

    For ``tool_source == 'mcp'`` rows the MCP server URL is validated against
    the SSRF guard (``validate_mcp_server_url``); stdio servers are rejected
    upstream by the parser and never reach here.

    Org admins attach published servers to their agents via ``POST /tools/agent``
    (gated on ``agent:update``); they do NOT author. Discover/parse are also
    platform-admin-only (probing a remote server is an authoring action).
    """
    current_user_id, user_profile = user_data

    # Authoring is platform-admin only.
    assert_platform_role(
        user_profile,
        "platform_admin",
        error_message="Only platform admins can author MCP servers",
    )

    # Validate the MCP server URL for MCP-sourced rows (SSRF + scheme guard).
    if tool_data.tool_source is ToolSource.MCP:
        if not tool_data.mcp_server_url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="MCP server URL is required for MCP tools",
            )
        ok, reason = validate_mcp_server_url(tool_data.mcp_server_url)
        if not ok:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=reason)

    tool, error = await tool_service.upsert_platform_tool(tool_data)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return tool


@tool_router.post(
    "/platform/{tool_id}/publish", response_model=PlatformTool
)
@tracer.start_as_current_span("tool.routes.publish_platform_tool")
async def publish_platform_tool(
    tool_id: UUID,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Publish a platform tool to the global catalog (platform-admin only).

    Flips ``is_published=True``; the server becomes visible to all org users
    in the tool panel. Existing attachments are unaffected.
    """
    current_user_id, user_profile = user_data
    assert_platform_role(
        user_profile,
        "platform_admin",
        error_message="Only platform admins can publish MCP servers",
    )
    tool, error = await tool_service.publish_platform_tool(tool_id, True)
    if error:
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
                if error == "Platform tool not found"
                else status.HTTP_400_BAD_REQUEST
            ),
            detail=error,
        )
    return tool


@tool_router.post(
    "/platform/{tool_id}/unpublish", response_model=PlatformTool
)
@tracer.start_as_current_span("tool.routes.unpublish_platform_tool")
async def unpublish_platform_tool(
    tool_id: UUID,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Unpublish a platform tool — revert to draft (platform-admin only).

    Hides the server from new attaches (org users no longer see it). Existing
    ``agent_tools`` attachments keep working (the worker reads them by join).
    """
    current_user_id, user_profile = user_data
    assert_platform_role(
        user_profile,
        "platform_admin",
        error_message="Only platform admins can unpublish MCP servers",
    )
    tool, error = await tool_service.publish_platform_tool(tool_id, False)
    if error:
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
                if error == "Platform tool not found"
                else status.HTTP_400_BAD_REQUEST
            ),
            detail=error,
        )
    return tool


@tool_router.put("/platform/{tool_id}", response_model=PlatformTool)
@tracer.start_as_current_span("tool.routes.update_platform_tool")
async def update_platform_tool(
    tool_id: UUID,
    tool_data: PlatformToolCreate,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Edit a platform tool by id (platform-admin only).

    Reconfigure an authored server (URL, headers, auth mode). Mirrors create's
    encryption + org-forcing but updates by ``id`` instead of upserting by name.
    """
    current_user_id, user_profile = user_data
    assert_platform_role(
        user_profile,
        "platform_admin",
        error_message="Only platform admins can edit MCP servers",
    )
    if tool_data.tool_source is ToolSource.MCP:
        if not tool_data.mcp_server_url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="MCP server URL is required for MCP tools",
            )
        ok, reason = validate_mcp_server_url(tool_data.mcp_server_url)
        if not ok:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=reason)
    tool, error = await tool_service.update_platform_tool(tool_id, tool_data)
    if error:
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
                if error == "Platform tool not found"
                else status.HTTP_400_BAD_REQUEST
            ),
            detail=error,
        )
    return tool


@tool_router.get("/platform/{tool_id}/usage")
@tracer.start_as_current_span("tool.routes.get_platform_tool_usage")
async def get_platform_tool_usage(
    tool_id: UUID,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """List the agents currently using a platform tool (platform-admin only).

    Powers the delete-confirm dialog's "used by N agents" warning list and the
    unpublish info banner. Returns ``{"count": int, "agents": [...]}`` where
    each agent is ``{agent_id, agent_name, organization_id}``.
    """
    current_user_id, user_profile = user_data
    assert_platform_role(
        user_profile,
        "platform_admin",
        error_message="Only platform admins can view platform tool usage",
    )
    agents, error = await tool_service.get_platform_tool_usage(tool_id)
    if error:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error)
    return {"count": len(agents or []), "agents": agents or []}


@tool_router.delete("/platform/{tool_id}")
@tracer.start_as_current_span("tool.routes.delete_platform_tool")
async def delete_platform_tool(
    tool_id: UUID,
    force: bool = False,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Delete a platform tool from the catalog (platform-admin only).

    Query param ``force=true`` allows deleting an MCP tool that is in use;
    the service then cascade-detaches its agent_tools rows first (audited
    below). Required for in-use tools.

    Guardrails (RFC §6.6):

    - **Legacy (code-backed) tools are never hard-deleted** (re-seeded on
      worker startup) → ``400``; steer to :func:`unpublish_platform_tool`.
    - **An MCP tool referenced by any agent** → ``409 in_use`` with the list
      of affected agents. The admin confirms via the type-to-confirm dialog
      and re-issues with ``?force=true``.
    - **``force=true``** cascade-detaches the agent_tools rows (audited below)
      and removes the platform_tools row.

    Prefer :func:`unpublish_platform_tool` for a reversible hide-from-catalog;
    delete is for permanent cleanup.
    """
    current_user_id, user_profile = user_data
    assert_platform_role(
        user_profile,
        "platform_admin",
        error_message="Only platform admins can delete MCP servers",
    )

    # When forcing, fetch the usage up front so the audit entry can name the
    # agents being detached (the service detaches them internally). For the
    # non-force path we only need the list if the service reports in_use.
    usage_for_audit: list = []
    if force:
        usage, usage_error = await tool_service.get_platform_tool_usage(tool_id)
        if usage_error:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=usage_error
            )
        usage_for_audit = usage or []

    deleted, error = await tool_service.delete_platform_tool(tool_id, force=force)

    if error == "in_use":
        # Build the 409 body listing the affected agents (fetch if we didn't
        # already for the force path).
        if not usage_for_audit:
            usage, _ = await tool_service.get_platform_tool_usage(tool_id)
            usage_for_audit = usage or []
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "in_use",
                "count": len(usage_for_audit),
                "agents": usage_for_audit,
                "message": (
                    "This tool is used by agents. Confirm in the dialog to "
                    "force-delete and detach it from all of them."
                ),
            },
        )
    if error == "legacy_tools_cannot_be_deleted":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "This tool is code-backed (a built-in tool) and is re-seeded on "
                "worker startup, so it cannot be hard-deleted. Unpublish it "
                "instead to hide it from the catalog."
            ),
        )
    if error == "Platform tool not found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Platform tool not found"
        )

    # Audit a force-delete: the actor, the tool, and the agents that just lost
    # the capability on their next call. No audit table exists yet — this is a
    # structured application log + OTEL span attributes (durable trail tracked
    # as a follow-up; see docs/03_implementation/mcp_integration_rfc.md).
    if force and usage_for_audit:
        span = trace.get_current_span()
        span.set_attribute("tool.force_delete", True)
        span.set_attribute("tool.deleted_id", str(tool_id))
        span.set_attribute("tool.detached_agent_count", len(usage_for_audit))
        span.set_attribute(
            "tool.detached_agent_ids",
            [a.get("agent_id") for a in usage_for_audit],
        )
        logger.info(
            "platform_admin force-deleted platform tool %s; detached %d agent(s): %s",
            str(tool_id),
            len(usage_for_audit),
            ", ".join(
                f"{a.get('agent_name') or a.get('agent_id')} ({a.get('agent_id')})"
                for a in usage_for_audit
            ),
        )

    return {"id": str(tool_id), "deleted": True}


@tool_router.post("/mcp/discover")
@tracer.start_as_current_span("tool.routes.discover_mcp_tools")
async def discover_mcp_tools(
    request: McpDiscoverRequest,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Discover the tools a remote MCP server exposes (in-memory probe).

    Validates the URL (SSRF guard), probes the server with JSON Streamable HTTP
    (``list_tools_json_http``), and returns sanitized tool definitions so the UI
    can preview what the agent will get before saving. Nothing is persisted.

    Gate: platform admin only (probing a remote server is an authoring action,
    RFC §6.6). Org admins attach already-published servers; they do not author.
    """
    current_user_id, user_profile = user_data
    assert_platform_role(
        user_profile,
        "platform_admin",
        error_message="Only platform admins can discover MCP tools",
    )

    ok, reason = validate_mcp_server_url(request.url)
    if not ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=reason)

    probe_headers = request.headers or {}
    logger.info(
        "MCP discover probe url=%s header_keys=%s has_authorization=%s",
        request.url,
        sorted(probe_headers.keys()),
        any(k.lower() == "authorization" for k in probe_headers),
    )
    config = McpServerConfig(url=request.url, headers=probe_headers)
    try:
        # Prefer JSON-only discovery — compatible with Twenty CRM and other
        # servers that mishandle SSE clients (Cursor/curl use this path).
        tool_defs = await list_tools_json_http(config)
    except McpJsonRpcError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Could not reach MCP server: {e}",
        )
    except httpx.HTTPStatusError as e:
        detail = format_mcp_client_error(e)
        logger.warning(
            "MCP discover failed for %s (header_keys=%s): %s",
            request.url,
            sorted(probe_headers.keys()),
            detail,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Could not reach MCP server: {detail}",
        )
    except Exception as e:
        detail = format_mcp_client_error(e)
        logger.warning(
            "MCP discover failed for %s (header_keys=%s): %s",
            request.url,
            sorted(probe_headers.keys()),
            detail,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Could not reach MCP server: {detail}",
        )

    return {
        "tools": [
            {
                "name": td.name,
                "description": td.description,
                "input_schema": td.input_schema,
            }
            for td in tool_defs
        ]
    }


@tool_router.post("/mcp/parse")
@tracer.start_as_current_span("tool.routes.parse_mcp_servers")
async def parse_mcp_servers(
    request: McpParseRequest,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Parse a pasted ``mcpServers`` JSON config into server configs + errors.

    The authoritative parser lives in
    :func:`shared.voice_agents.tools.mcp.security.parse_mcp_servers_json` so the
    frontend has a single source of truth (no duplicated TS parser). Returns
    valid HTTP server configs and per-entry errors (e.g. rejected stdio
    entries) for the UI to render.

    Gate: platform admin only (authoring action, RFC §6.6).
    """
    current_user_id, user_profile = user_data
    assert_platform_role(
        user_profile,
        "platform_admin",
        error_message="Only platform admins can parse MCP config",
    )

    result = parse_mcp_servers_json(request.raw)
    return {
        "servers": [s.model_dump() for s in result.servers],
        "errors": [e.model_dump() for e in result.errors],
    }


@tool_router.get("/platform", response_model=List[PlatformTool])
@tracer.start_as_current_span("tool.routes.get_platform_tools")
async def get_platform_tools(
    only_active: bool = True,
    include_drafts: bool = Query(default=False),
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Get platform tools visible to the caller (publish lifecycle, RFC §6.6).

    Org users see only **published** rows (``is_published=True`` + ``is_active``)
    — the global catalog they can attach to their agents. Platform admins may
    pass ``include_drafts=true`` to also see drafts (the authoring/management
    view). A non-platform-admin passing ``include_drafts=true`` is rejected
    (403) — drafts are platform-admin-only.

    The org-scoped custom tier is retired; all published servers are global, so
    there is no per-org filter. The worker reads attached tools by join (not
    via this listing), so it is unaffected.
    """
    current_user_id, user_profile = user_data

    if include_drafts:
        assert_platform_role(
            user_profile,
            "platform_admin",
            error_message="Only platform admins can view draft MCP servers",
        )

    tools, error = await tool_service.get_platform_tools(
        only_active,
        include_drafts=include_drafts,
    )
    if error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error
        )
    return tools


# Agent Tools
@tool_router.post("/agent", response_model=AgentToolResponse)
@tracer.start_as_current_span("tool.routes.configure_agent_tool")
async def configure_agent_tool(
    agent_tool_data: AgentToolCreate,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Configure a tool for an agent."""
    current_user_id, user_profile = user_data

    # Get agent to check organization
    agent, error = await voice_agent_service.get_agent_by_id(agent_tool_data.agent_id)
    if error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found"
        )

    # Configuring a tool mutates agent capability → agent:update.
    assert_has_permission(
        user_profile,
        "agent",
        "update",
        agent.organization_id,
        error_message="Insufficient permissions to configure tools for this agent",
    )

    agent_tool, error = await tool_service.configure_agent_tool(agent_tool_data)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return agent_tool


@tool_router.get("/agent/{agent_id}", response_model=List[AgentToolResponse])
@tracer.start_as_current_span("tool.routes.get_agent_tools")
async def get_agent_tools(
    agent_id: UUID,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Get all tools configured for an agent."""
    current_user_id, user_profile = user_data

    # Get agent to check organization
    agent, error = await voice_agent_service.get_agent_by_id(agent_id)
    if error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found"
        )

    assert_has_permission(
        user_profile,
        "agent",
        "read",
        agent.organization_id,
        error_message="Insufficient permissions to view tools for this agent",
    )

    tools, error = await tool_service.get_agent_tools(agent_id)
    if error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error
        )
    return tools


async def _resolve_tool_auth_config(tool_name: str) -> dict | None:
    """Resolve the OAuth ``auth_config`` dict for a tool by name.

    DB-first resolution so MCP-sourced ``platform_tools`` (which have no
    in-tree ``BaseTool`` subclass in the platform tool registry) flow through the
    same OAuth start/callback endpoints as legacy tools. The DB row's
    ``auth_config`` is populated for legacy tools by
    ``PlatformToolRegistry.sync_with_db`` and for MCP tools by the platform
    seed (see ``docs/03_implementation/mcp_integration_rfc.md``).

    Falls back to the legacy platform tool registry for back-compat if no DB row
    carries ``auth_config`` (defensive — synced/seeded rows always have it).

    Args:
        tool_name: The ``platform_tools.name`` (also the legacy registry key).

    Returns:
        The ``auth_config`` dict (``provider`` / ``auth_url`` / ``token_url``
        / ``scopes`` / ``access_type`` / ``prompt``) or ``None`` if the tool
        is unknown to both the DB and the legacy registry. A ``None`` return
        is treated by the callers as a 404 — a tool without an OAuth config
        cannot start an OAuth flow.

    Notes:
        - Coexistence (RFC §1.1): the legacy registry is a *fallback*, never
          deleted; MCP rows resolve from the DB and never touch it.
        - ``TokenRefreshService`` reads the same ``auth_config`` column to
          refresh tokens, so an MCP tool whose config is resolved here is
          also auto-refreshed with no further wiring.
    """
    # 1. DB-first: platform_tools row by name.
    tools, _ = await tool_service.get_platform_tools(only_active=False, include_drafts=True)
    row = next((t for t in tools if t.name == tool_name), None)
    if row is not None and row.auth_config:
        cfg = row.auth_config
        if isinstance(cfg, dict):
            return cfg
        # Pydantic BaseAuthConfig (legacy rows may store a model).
        if hasattr(cfg, "model_dump"):
            return cfg.model_dump()
        return dict(cfg)

    # 2. Legacy registry fallback (back-compat for rows lacking auth_config).
    from shared.voice_agents.tools.base.platform_tool_registry import platform_tool_registry

    tool_class = platform_tool_registry.get_tool_class(tool_name)
    if tool_class is not None:
        metadata = tool_class().metadata
        if metadata.auth_config:
            return metadata.auth_config
    return None


# OAuth Handlers
@tool_router.get("/auth/{tool_name}")
@tracer.start_as_current_span("tool.routes.start_oauth")
async def start_oauth(
    tool_name: str,
    agent_id: UUID,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Start OAuth flow for a specific tool.

    Resolves the tool's OAuth config from the ``platform_tools`` DB row first
    (so MCP-sourced tools work), falling back to the legacy platform tool registry.
    Client credentials come from the ``GOOGLE_OAUTH_TOOL_*`` env vars via
    :class:`OAuthProviderManager`; scopes / auth_url / access_type / prompt
    come from the resolved ``auth_config``.
    """
    auth_config = await _resolve_tool_auth_config(tool_name)
    if not auth_config:
        raise HTTPException(status_code=404, detail="Tool not found")

    client_id = os.getenv("GOOGLE_OAUTH_TOOL_CLIENT_ID", "")
    redirect_uri = os.getenv("GOOGLE_OAUTH_TOOL_REDIRECT_URI", "")

    if not client_id or not redirect_uri:
        raise HTTPException(
            status_code=500,
            detail="Google OAuth credentials not configured. Please set GOOGLE_OAUTH_TOOL_CLIENT_ID and GOOGLE_OAUTH_TOOL_REDIRECT_URI environment variables.",
        )

    # Encode state with agent_id and tool_name
    state_data = {
        "agent_id": str(agent_id),
        "tool_name": tool_name,
        "timestamp": datetime.now().isoformat(),
    }
    state = base64.urlsafe_b64encode(json.dumps(state_data).encode()).decode()

    # Build OAuth URL with dynamic parameters
    scopes = auth_config.get("scopes") or []
    auth_params = {
        "client_id": quote(client_id),
        "redirect_uri": quote(redirect_uri),
        "response_type": "code",
        "scope": quote(" ".join(scopes)),
        "state": quote(state),
    }

    # Add access_type and prompt if configured (required for refresh_token)
    if auth_config.get("access_type"):
        auth_params["access_type"] = quote(auth_config["access_type"])
    if auth_config.get("prompt"):
        auth_params["prompt"] = quote(auth_config["prompt"])

    # Construct URL
    auth_query = "&".join(f"{k}={v}" for k, v in auth_params.items())
    auth_url = f"{auth_config['auth_url']}?{auth_query}"
    return {"auth_url": auth_url}


@tool_router.get("/callback")
async def oauth_callback(code: str, state: str):
    """Handle OAuth callback and save tokens."""
    import httpx

    # 1. Decode state to get agent_id and tool_name
    try:
        decoded_state = json.loads(base64.urlsafe_b64decode(state).decode())
        agent_id = UUID(decoded_state["agent_id"])
        tool_name = decoded_state["tool_name"]

        # Optional: Add timestamp validation to prevent replay attacks
        # if state_timestamp:
        #     state_time = datetime.fromisoformat(state_timestamp)
        #     if (datetime.now() - state_time).total_seconds() > 300:  # 5 minutes
        #         raise HTTPException(status_code=400, detail="OAuth state has expired")
    except (KeyError, ValueError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid OAuth state: {str(e)}")

    # 2. Resolve tool OAuth config (DB-first, legacy registry fallback) so
    #    MCP-sourced tools flow through the same callback as legacy tools.
    auth_config = await _resolve_tool_auth_config(tool_name)
    if not auth_config:
        raise HTTPException(status_code=404, detail="Tool not found")

    # Get OAuth provider manager singleton
    oauth_manager = get_oauth_manager()

    # Extract provider and token_url using singleton manager
    provider, token_url = oauth_manager.extract_oauth_config(auth_config)
    
    if not token_url:
        raise HTTPException(
            status_code=500, detail="Tool does not have token_url configured"
        )

    # Validate provider using singleton manager
    is_valid, required_env_vars = oauth_manager.validate_provider(provider)
    if not is_valid:
        raise HTTPException(
            status_code=400, detail=f"Unsupported OAuth provider: {provider}"
        )

    # 4. Exchange authorization code for tokens
    # Build OAuth data using singleton manager (includes client_id and client_secret)
    try:
        credentials = oauth_manager.get_credentials(provider)
        if not credentials.client_id or not credentials.client_secret or not credentials.redirect_uri:
            raise HTTPException(
                status_code=500,
                detail=f"{provider.title()} OAuth credentials not configured. Please set {', '.join(required_env_vars)} environment variables.",
            )

        oauth_data = oauth_manager.get_auth_data(
            provider=provider,
            flow="auth",
            code=code,
            redirect_uri=credentials.redirect_uri,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=500, detail=str(e)
        )

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                token_url,
                data=oauth_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
            token_data = response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Failed to exchange authorization code for tokens: {e.response.text}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error exchanging tokens: {str(e)}"
        )

    # 5. Extract tokens and calculate expiration
    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")
    expires_in = token_data.get("expires_in", 3600)

    if not access_token:
        raise HTTPException(
            status_code=500, detail="No access_token returned from OAuth provider"
        )

    sensitive_config = {
        "access_token": access_token,
    }

    # Only add refresh_token if it was returned (requires access_type=offline)
    if refresh_token:
        sensitive_config["refresh_token"] = refresh_token
    else:
        logger.warning(
            f"OAuth callback did NOT receive refresh_token for tool {tool_name}. "
            "Token will not be auto-refreshable. User will need to re-authenticate when token expires."
        )

    # Calculate expiration time
    if expires_in:
        sensitive_config["expires_at"] = datetime.now().timestamp() + expires_in
    else:
        sensitive_config["expires_at"] = (
            datetime.now().timestamp() + 3600
        )  # Default 1 hour

    # 6. Get tool_id from DB
    tools, _ = await tool_service.get_platform_tools(only_active=False, include_drafts=True)
    tool_id = next((t.id for t in tools if t.name == tool_name), None)

    if not tool_id:
        raise HTTPException(status_code=404, detail="Tool not found in DB")

    # 7. Save to agent_tools
    await tool_service.configure_agent_tool(
        AgentToolCreate(
            agent_id=agent_id,
            tool_id=tool_id,
            sensitive_config=sensitive_config,
            is_enabled=True,
        )
    )

    return {"message": "Successfully authenticated"}


@tool_router.put("/agent/{agent_tool_id}", response_model=AgentToolResponse)
@tracer.start_as_current_span("tool.routes.update_agent_tool")
async def update_agent_tool(
    agent_tool_id: UUID,
    update_data: AgentToolUpdate,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Update an agent tool configuration."""
    current_user_id, user_profile = user_data
    # CRIT: must verify the caller is an admin on the agent's org before
    # allowing this write (any logged-in user could otherwise rewrite the
    # tool config by guessing the UUID).
    await _assert_agent_tool_admin(agent_tool_id, user_profile)

    updated_tool, error = await tool_service.update_agent_tool(
        agent_tool_id, update_data
    )
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return updated_tool


@tool_router.post("/agent/{agent_tool_id}/logout", response_model=AgentToolResponse)
@tracer.start_as_current_span("tool.routes.logout_agent_tool")
async def logout_agent_tool(
    agent_tool_id: UUID,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Logout from a tool by clearing its sensitive config (tokens)."""
    current_user_id, user_profile = user_data
    # CRIT: any logged-in user could otherwise clear a real user's
    # OAuth tokens by guessing the agent_tool_id.
    await _assert_agent_tool_admin(agent_tool_id, user_profile)

    updated_tool, error = await tool_service.update_agent_tool(
        agent_tool_id, AgentToolUpdate(sensitive_config=None)
    )
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return updated_tool


@tool_router.put("/agent/{agent_tool_id}/api-key", response_model=AgentToolResponse)
@tracer.start_as_current_span("tool.routes.set_api_key")
async def set_api_key(
    agent_tool_id: UUID,
    api_key: str = Body(..., embed=True, description="API key to store in sensitive_config"),
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Save or update API key in sensitive_config for a tool."""
    current_user_id, user_profile = user_data
    # CRIT: most dangerous endpoint — any logged-in user could otherwise
    # overwrite a real user's Google API key by guessing the agent_tool_id.
    await _assert_agent_tool_admin(agent_tool_id, user_profile)

    if not api_key or not api_key.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="API key cannot be empty"
        )

    # Update sensitive config with API key
    updated_tool, error = await tool_service.update_agent_tool(
        agent_tool_id, AgentToolUpdate(sensitive_config={"api_key": api_key.strip()})
    )
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return updated_tool


@tool_router.delete("/agent/{agent_tool_id}")
@tracer.start_as_current_span("tool.routes.delete_agent_tool")
async def delete_agent_tool(
    agent_tool_id: UUID,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Delete an agent tool configuration permanently."""
    current_user_id, user_profile = user_data
    # CRIT: any logged-in user could otherwise permanently delete a tool
    # configuration by guessing the agent_tool_id.
    await _assert_agent_tool_admin(agent_tool_id, user_profile)

    deleted, error = await tool_service.delete_agent_tool(agent_tool_id)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Agent tool not found"
        )
    return {"id": str(agent_tool_id), "deleted": True}
