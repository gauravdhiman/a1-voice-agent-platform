"""
Tool API routes for the platform.
"""

import base64
import inspect
import logging
import math
import os
import secrets
from datetime import datetime, timezone
from typing import Any, List, Optional
from urllib.parse import urlencode
from uuid import UUID

import httpx
from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from opentelemetry import trace
from pydantic import BaseModel, Field
from src.auth.dependencies import assert_has_permission, assert_platform_role
from src.auth.middleware import get_authenticated_user
from src.auth.models import UserProfile
from src.billing.entitlement_service import entitlement_service

from shared.config import settings
from shared.voice_agents.service import voice_agent_service
from shared.voice_agents.tool_models import (
    AgentToolCreate,
    AgentToolResponse,
    AgentToolUpdate,
    PlatformTool,
    PlatformToolCreate,
    ToolSource,
)
from shared.voice_agents.tool_service import tool_service
from shared.voice_agents.tools.base.oauth_provider_utils import get_oauth_manager
from shared.voice_agents.tools.base.oauth_support import (
    get_oauth_client_auth_method,
    is_supported_oauth_client_auth_method,
    sanitize_oauth_config,
    validate_oauth_endpoint_url,
)
from shared.voice_agents.tools.mcp.errors import format_mcp_client_error
from shared.voice_agents.tools.mcp.json_http_client import (
    McpJsonRpcError,
    list_tools_json_http,
)
from shared.voice_agents.tools.mcp.models import McpServerConfig
from shared.voice_agents.tools.mcp.oauth import (
    build_mcp_authorization_url,
    create_mcp_oauth_state,
    decode_mcp_oauth_state,
    discover_mcp_oauth_config,
    pkce_challenge,
    register_mcp_oauth_client,
)
from shared.voice_agents.tools.mcp.security import (
    is_sensitive_mcp_header,
    parse_mcp_servers_json,
    validate_mcp_server_url,
)

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)
tool_router = APIRouter(prefix="/api/v1/tools", tags=["Tools"])
DEFAULT_OAUTH_TOKEN_LIFETIME_SECONDS = 3600


def _oauth_expires_at(expires_in: Any) -> float:
    """Convert a provider expiry value into a safe absolute timestamp.

    Args:
        expires_in: OAuth provider's lifetime value. Providers sometimes
            serialize this standard field as a string or omit it entirely.

    Returns:
        An absolute Unix timestamp using a one-hour fallback when the value is
        missing, non-numeric, or non-positive.
    """
    try:
        lifetime_seconds = float(expires_in)
        if lifetime_seconds <= 0 or not math.isfinite(lifetime_seconds):
            raise ValueError("expires_in must be positive")
    except (TypeError, ValueError):
        lifetime_seconds = DEFAULT_OAUTH_TOKEN_LIFETIME_SECONDS
    return datetime.now(timezone.utc).timestamp() + lifetime_seconds


def _validate_oauth_url(url: str, field_name: str) -> None:
    """Reject an OAuth endpoint that could leak a code or grant.

    Args:
        url: Endpoint or redirect URI used by the OAuth flow.
        field_name: Human-readable configuration field for the API error.

    Raises:
        HTTPException: If the URL is not HTTPS-safe (or explicitly allowed
            loopback development URL).
    """
    valid, reason = validate_oauth_endpoint_url(
        url,
        resolve_dns=field_name.lower() != "redirect uri",
        allow_loopback_redirect=field_name.lower() == "redirect uri",
    )
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid OAuth {field_name}: {reason}",
        )


def _validate_public_mcp_headers(headers: Optional[dict[str, str]]) -> None:
    """Reject credential-bearing headers from plaintext MCP metadata.

    Args:
        headers: Static headers submitted for a platform MCP tool.

    Raises:
        HTTPException: If a conventional credential header is supplied. The
            caller should place it in ``mcp_secret_headers_input`` so the
            service encrypts it before persistence.
    """
    for header_name in headers or {}:
        if is_sensitive_mcp_header(str(header_name)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"MCP header '{header_name}' carries credentials and must "
                    "be supplied through the encrypted secret-header field"
                ),
            )


# --- MCP configure-from-UI request models ---------------------------------
# Lightweight payloads for the "Add MCP server" flow. Discover and parse are
# in-memory (nothing persisted); create reuses PlatformToolCreate.
class PlatformToolPremiumUpdate(BaseModel):
    """Body for flipping a platform tool's premium flag.

    Attributes:
        is_premium: True gates the tool behind the plan's ``premium_tools``
            feature (attach 403 when off); False makes it available to all
            plans. Already-connected agents keep the tool either way.
    """

    is_premium: bool = Field(
        ...,
        description=("True to gate the tool behind the premium_tools plan feature"),
    )


class McpDiscoverRequest(BaseModel):
    """In-memory discover request: test a remote MCP server's tools.

    Attributes:
        url: Streamable HTTP endpoint of the MCP server to probe.
        headers: Static headers already resolved by the UI (public headers
            plus any secret-header JSON the admin typed for this probe).
        tool_id: When editing an existing MCP tool, the platform_tools id.
            The backend decrypts stored ``mcp_server_secret_headers`` and
            merges them into the probe so the admin does not have to re-paste
            secrets just to re-test. Request ``headers`` win on key conflicts
            (typed overrides).
        test_api_key: Transient key substituted into any ``{{KEY}}`` placeholder
            found in stored secret headers. Never persisted. Required only when
            stored secrets use the placeholder and the admin did not send a
            fully-resolved override in ``headers``.
    """

    url: str
    headers: dict[str, str] = Field(default_factory=dict)
    tool_id: Optional[UUID] = None
    test_api_key: Optional[str] = None


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
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    if agent_tool is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent tool not found",
        )

    agent, agent_error = await voice_agent_service.get_agent_by_id(agent_tool.agent_id)
    if agent_error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=agent_error)
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
    _, user_profile = user_data

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
        _validate_public_mcp_headers(tool_data.mcp_server_headers)

    tool, error = await tool_service.upsert_platform_tool(tool_data)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return tool


@tool_router.post("/platform/{tool_id}/publish", response_model=PlatformTool)
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


@tool_router.post("/platform/{tool_id}/unpublish", response_model=PlatformTool)
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


@tool_router.post("/platform/{tool_id}/premium", response_model=PlatformTool)
@tracer.start_as_current_span("tool.routes.set_platform_tool_premium")
async def set_platform_tool_premium(
    tool_id: UUID,
    premium_update: PlatformToolPremiumUpdate,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Set or clear a platform tool's premium flag (platform-admin only).

    Flips ``platform_tools.is_premium`` so the tool card shows a Premium
    badge in every org's catalog and attach is gated on the plan's
    ``premium_tools`` feature (403 at ``POST /tools/agent`` when off).
    Existing ``agent_tools`` attachments keep working regardless of the
    flag.
    """
    current_user_id, user_profile = user_data
    assert_platform_role(
        user_profile,
        "platform_admin",
        error_message="Only platform admins can mark tools premium",
    )
    tool, error = await tool_service.set_platform_tool_premium(
        tool_id, premium_update.is_premium
    )
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
        _validate_public_mcp_headers(tool_data.mcp_server_headers)
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error
        )
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

    Validates the URL (SSRF guard), probes the server with MCP Streamable HTTP
    (JSON or SSE responses via ``list_tools_json_http``), and returns sanitized
    tool definitions so the UI can preview what the agent will get before
    saving. Nothing is persisted.

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

    probe_headers = dict(request.headers or {})
    if request.tool_id is not None:
        merged, merge_error = await tool_service.merge_stored_mcp_secret_headers(
            request.tool_id,
            probe_headers,
            test_api_key=request.test_api_key,
        )
        if merge_error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=merge_error,
            )
        probe_headers = merged

    logger.info(
        "MCP discover probe header_keys=%s has_authorization=%s tool_id=%s",
        sorted(probe_headers.keys()),
        any(k.lower() == "authorization" for k in probe_headers),
        str(request.tool_id) if request.tool_id else None,
    )
    config = McpServerConfig(url=request.url, headers=probe_headers)
    try:
        # Prefer JSON-only discovery — compatible with Twenty CRM and other
        # servers that mishandle SSE clients (Cursor/curl use this path).
        tool_defs = await list_tools_json_http(config)
    except McpJsonRpcError as e:
        logger.warning("MCP discover returned a JSON-RPC error (%s)", type(e).__name__)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not reach MCP server",
        )
    except httpx.HTTPStatusError as e:
        detail = format_mcp_client_error(e)
        logger.warning(
            "MCP discover failed (header_keys=%s; transport=%s)",
            sorted(probe_headers.keys()),
            type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Could not reach MCP server: {detail}",
        )
    except Exception as e:
        detail = format_mcp_client_error(e)
        logger.warning(
            "MCP discover failed (header_keys=%s; transport=%s)",
            sorted(probe_headers.keys()),
            type(e).__name__,
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
    """Parse a pasted MCP host JSON config into server configs + errors.

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
    """Configure a tool for an agent.

    MCP integrations that use organization API-key authentication cannot be
    attached without the key. A platform-owned literal fallback keeps the key
    optional, while an organization key is encrypted by the tool service and
    selected at runtime without changing the platform configuration.
    """
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

    # Premium tools are catalog-visible but gated at attach time: the org's
    # plan must entitle the 'premium_tools' feature (check_feature → 403).
    platform_tool, tool_error = await tool_service.get_platform_tool_by_id(
        agent_tool_data.tool_id
    )
    if tool_error and tool_error != "Platform tool not found":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=tool_error,
        )
    if platform_tool is not None and platform_tool.is_premium:
        if not await entitlement_service.check_feature(
            agent.organization_id, "premium_tools"
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Premium tools are not included in your current plan. "
                    "Upgrade your plan to connect this tool."
                ),
            )

    tool_source = getattr(platform_tool, "tool_source", None)
    tool_source_value = getattr(tool_source, "value", tool_source)
    if (
        platform_tool is not None
        and tool_source_value == "mcp"
        and platform_tool.auth_type == "api_key"
        and platform_tool.requires_auth
    ):
        sensitive_config = agent_tool_data.sensitive_config or {}
        organization_api_key = sensitive_config.get("api_key")
        if (
            not isinstance(organization_api_key, str)
            or not organization_api_key.strip()
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Organization API key is required before connecting this "
                    "MCP tool."
                ),
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
    tools, _ = await tool_service.get_platform_tools(
        only_active=False, include_drafts=True
    )
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
    from shared.voice_agents.tools.base.platform_tool_registry import (
        platform_tool_registry,
    )

    tool_class = platform_tool_registry.get_tool_class(tool_name)
    if tool_class is not None:
        metadata = tool_class().metadata
        if metadata.auth_config:
            return metadata.auth_config
    return None


# OAuth Handlers
def _is_mcp_oauth_config(
    auth_config: dict,
    platform_tool: Optional[PlatformTool] = None,
) -> bool:
    """Return whether a tool should use MCP's provider-neutral OAuth flow.

    MCP host metadata may identify the vendor (for example, ``linear`` or
    ``notion``) rather than the protocol as the provider. Native providers
    such as Google remain on the existing provider-specific flow even when
    their server is MCP-backed.
    """
    provider = str(auth_config.get("provider", "")).strip().lower()
    oauth_mode = str(auth_config.get("oauth_mode", "")).strip().lower()
    if (
        provider in {"mcp", "mcp_oauth", "mcp-oauth"}
        or bool(auth_config.get("mcp_oauth"))
        or oauth_mode in {"generic", "mcp", "mcp_oauth", "mcp-oauth"}
    ):
        return True

    tool_source = getattr(platform_tool, "tool_source", None)
    is_mcp_tool = getattr(tool_source, "value", tool_source) == ToolSource.MCP.value
    if not is_mcp_tool:
        return False
    if not provider:
        return bool(auth_config.get("auth_url") or auth_config.get("token_url"))

    # A vendor label is protocol metadata when the provider is not one of our
    # native OAuth integrations. The refresh service uses the same rule.
    try:
        get_oauth_manager().get_credentials(provider)
    except ValueError:
        return True
    return False


def _resolve_oauth_client_metadata(
    auth_config: dict[str, Any], provider: str
) -> dict[str, Optional[str]]:
    """Resolve OAuth client metadata from the tool row or native registry.

    Args:
        auth_config: OAuth metadata resolved from ``platform_tools`` or the
            legacy platform-tool registry.
        provider: Provider identifier extracted from ``auth_config``.

    Returns:
        A mapping containing ``client_id``, ``client_secret``,
        ``redirect_uri``, and ``token_endpoint_auth_method``. Values in the
        tool metadata take precedence so dynamically registered providers can
        work without being added to the native provider registry.

    Notes:
        Native provider environment variables remain the default for existing
        integrations. The generic metadata fallback is intentionally limited
        to OAuth client fields and never logs their values.
    """
    credentials = None
    try:
        credentials = get_oauth_manager().get_credentials(provider)
    except ValueError:
        # Unknown providers are valid when the tool row carries complete OAuth
        # metadata. The refresh service applies the same fallback rule.
        pass

    provider_env_prefix = provider.upper().replace("-", "_")
    return {
        "client_id": str(
            auth_config.get("client_id")
            or getattr(credentials, "client_id", None)
            or os.getenv(f"{provider_env_prefix}_OAUTH_TOOL_CLIENT_ID", "")
            or ""
        ),
        "client_secret": str(
            getattr(credentials, "client_secret", None)
            or os.getenv(f"{provider_env_prefix}_OAUTH_TOOL_CLIENT_SECRET", "")
            or ""
        ),
        "redirect_uri": str(
            auth_config.get("redirect_uri")
            or getattr(credentials, "redirect_uri", None)
            or os.getenv(f"{provider_env_prefix}_OAUTH_TOOL_REDIRECT_URI", "")
            or os.getenv("OAUTH_TOOL_REDIRECT_URI", "")
            or ""
        ),
        "token_endpoint_auth_method": str(
            auth_config.get("token_endpoint_auth_method")
            or auth_config.get("client_auth_method")
            or ""
        ).lower(),
    }


async def _resolve_stored_oauth_client_secret(tool_name: str) -> Optional[str]:
    """Resolve a confidential OAuth client secret from encrypted storage.

    The public ``auth_config`` JSONB is intentionally not a secret store. This
    helper is used only by the backend callback and never places the value in a
    response, log, or encrypted OAuth state payload.
    """
    resolver = getattr(tool_service, "get_platform_tool_oauth_client_secret", None)
    if resolver is None:
        return None
    result = resolver(tool_name)
    if not inspect.isawaitable(result):
        # Defensive compatibility for isolated route tests and alternate tool
        # service implementations; production uses the async service method.
        return None
    result = await result
    secret, error = result
    if error and error != "Platform tool not found":
        logger.warning("OAuth client secret lookup failed for %s", tool_name)
    return secret


async def _resolve_platform_tool_by_name(tool_name: str) -> Optional[PlatformTool]:
    """Resolve a platform tool row for MCP OAuth server URL metadata."""
    tools, _ = await tool_service.get_platform_tools(
        only_active=False,
        include_drafts=True,
    )
    return next((tool for tool in tools if tool.name == tool_name), None)


async def _discover_and_persist_mcp_tool_catalog(
    tool_name: str, access_token: str
) -> int:
    """Discover and persist an MCP server's public function catalog.

    This helper is intentionally called after OAuth succeeds for both the
    platform-admin discovery flow and an Org Admin's agent connection. The
    bearer token is used only for this one ``tools/list`` request; it is never
    written to ``platform_tools``. Org runtime calls continue to use the
    agent's own encrypted OAuth connection, so a platform discovery OAuth can
    never become an agent credential.

    Args:
        tool_name: Platform tool name whose remote server should be queried.
        access_token: Short-lived bearer obtained from the MCP OAuth callback.

    Returns:
        Number of functions discovered and persisted.

    Raises:
        RuntimeError: If the MCP row is missing, has no URL, or its catalog
            update fails.
        Exception: Transport/protocol errors from the MCP server are allowed
            to propagate to the caller for route-specific handling.
    """
    platform_tool = await _resolve_platform_tool_by_name(tool_name)
    if platform_tool is None or not platform_tool.mcp_server_url:
        raise RuntimeError("MCP tool not found or has no server URL")
    mcp_url_ok, mcp_url_reason = validate_mcp_server_url(platform_tool.mcp_server_url)
    if not mcp_url_ok:
        raise RuntimeError(f"Invalid MCP server URL: {mcp_url_reason}")

    headers = dict(platform_tool.mcp_server_headers or {})
    # OAuth bearer credentials always win over a stale static Authorization
    # header in a copied host configuration.
    for key in list(headers):
        if key.lower() == "authorization":
            del headers[key]
    headers["Authorization"] = f"Bearer {access_token}"

    tool_defs = await list_tools_json_http(
        McpServerConfig(
            url=platform_tool.mcp_server_url,
            name=platform_tool.mcp_server_name or platform_tool.name,
            headers=headers,
        )
    )
    schema = {
        "functions": [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.input_schema or {},
            }
            for tool in tool_defs
        ]
    }
    _, update_error = await tool_service.update_platform_tool_functions_schema(
        platform_tool.id, schema
    )
    if update_error:
        raise RuntimeError(update_error)
    return len(tool_defs)


def _mcp_oauth_redirect_uri(auth_config: dict) -> str:
    """Resolve the callback URI used by an MCP authorization server."""
    return str(
        auth_config.get("redirect_uri")
        or os.getenv("MCP_OAUTH_REDIRECT_URI")
        or f"{settings.api_base_url.rstrip('/')}/api/v1/tools/callback"
    )


async def _assert_agent_oauth_admin(agent_id: UUID, user_profile: UserProfile) -> None:
    """Require agent-update permission before starting an OAuth grant flow.

    OAuth callback state is deliberately trusted only after this check. Without
    it, any authenticated user who guessed an agent UUID could start a flow and
    attach their authorization grant to that agent.
    """
    agent, error = await voice_agent_service.get_agent_by_id(agent_id)
    if error or agent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )
    assert_has_permission(
        user_profile,
        "agent",
        "update",
        agent.organization_id,
        error_message="Insufficient permissions to connect tools for this agent",
    )


async def _start_mcp_oauth(
    tool_name: str,
    agent_id: Optional[UUID],
    auth_config: dict,
    *,
    oauth_flow: str = "mcp",
    tool_id: Optional[UUID] = None,
) -> dict[str, str]:
    """Start an MCP OAuth authorization-code + PKCE flow.

    MCP OAuth endpoints are either supplied in the platform definition or
    discovered from the server's protected-resource metadata. A client ID may
    be configured globally, embedded as a public client ID, or obtained via
    Dynamic Client Registration. No platform API key is required for this
    setup flow.
    """
    platform_tool = await _resolve_platform_tool_by_name(tool_name)
    if platform_tool is None or not platform_tool.mcp_server_url:
        raise HTTPException(status_code=404, detail="MCP tool not found")
    mcp_url_ok, mcp_url_reason = validate_mcp_server_url(platform_tool.mcp_server_url)
    if not mcp_url_ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid MCP server URL: {mcp_url_reason}",
        )

    try:
        resolved = await discover_mcp_oauth_config(
            platform_tool.mcp_server_url,
            auth_config,
        )
    except Exception as exc:
        logger.warning(
            "MCP OAuth metadata discovery failed for %s (%s)",
            tool_name,
            type(exc).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not discover MCP OAuth metadata",
        ) from None

    token_endpoint_auth_method = get_oauth_client_auth_method(resolved) or ""
    if not is_supported_oauth_client_auth_method(token_endpoint_auth_method):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "MCP OAuth uses an unsupported token endpoint client "
                f"authentication method ({token_endpoint_auth_method}); "
                "manual reauthorization or a provider adapter is required"
            ),
        )

    redirect_uri = _mcp_oauth_redirect_uri(resolved)
    _validate_oauth_url(str(resolved["auth_url"]), "authorization endpoint")
    _validate_oauth_url(str(resolved["token_url"]), "token endpoint")
    _validate_oauth_url(redirect_uri, "redirect URI")
    client_id = str(resolved.get("client_id") or os.getenv("MCP_OAUTH_CLIENT_ID") or "")
    if not client_id and resolved.get("registration_endpoint"):
        try:
            _validate_oauth_url(
                str(resolved["registration_endpoint"]),
                "dynamic client registration endpoint",
            )
            client_id = await register_mcp_oauth_client(
                str(resolved["registration_endpoint"]),
                redirect_uri=redirect_uri,
            )
        except Exception as exc:
            logger.warning(
                "MCP OAuth client registration failed for %s (%s)",
                tool_name,
                type(exc).__name__,
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Could not register an MCP OAuth client",
            ) from None
    if not client_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "MCP OAuth requires a public client ID. Configure MCP_OAUTH_CLIENT_ID "
                "or enable Dynamic Client Registration for this server."
            ),
        )

    # Persist the resolved, non-secret metadata before issuing an authorization
    # URL. Without this write, a discovery-only MCP configuration could connect
    # successfully once but leave the background refresher without its token
    # endpoint on the next sweep. The dedicated service method strips any
    # legacy credential fields again at the database boundary.
    persist_metadata = getattr(
        tool_service, "update_platform_tool_oauth_metadata", None
    )
    if persist_metadata is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="MCP OAuth metadata storage is not configured",
        )
    metadata_to_persist = sanitize_oauth_config(resolved)
    metadata_to_persist.update(
        {
            "provider": "mcp",
            "client_id": client_id,
            "oauth_mode": "generic",
            "mcp_oauth": True,
        }
    )
    persist_result = persist_metadata(platform_tool.id, metadata_to_persist)
    if inspect.isawaitable(persist_result):
        persisted, persist_error = await persist_result
    else:
        # Keep isolated route tests and older alternate ToolService adapters
        # compatible; production always uses the async method above.
        persisted, persist_error = True, None
    if not persisted:
        logger.error(
            "Could not persist MCP OAuth metadata for %s (%s)",
            tool_name,
            type(persist_error).__name__ if persist_error else "unknown_error",
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not persist MCP OAuth metadata",
        )

    verifier = secrets.token_urlsafe(64)
    resource = str(resolved.get("resource") or platform_tool.mcp_server_url)
    state_data = {
        "oauth_flow": oauth_flow,
        "tool_name": tool_name,
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "token_url": str(resolved["token_url"]),
        "resource": resource,
        "code_verifier": verifier,
        "token_endpoint_auth_method": token_endpoint_auth_method.lower(),
    }
    if agent_id is not None:
        state_data["agent_id"] = str(agent_id)
    if tool_id is not None:
        state_data["tool_id"] = str(tool_id)
    state = create_mcp_oauth_state(state_data)
    return {
        "auth_url": build_mcp_authorization_url(
            str(resolved["auth_url"]),
            client_id=client_id,
            redirect_uri=redirect_uri,
            state=state,
            code_challenge=pkce_challenge(verifier),
            scopes=[str(scope) for scope in resolved.get("scopes") or []],
            resource=resource,
        )
    }


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
    Registered native client credentials come from the provider environment via
    :class:`OAuthProviderManager`; dynamically configured providers use client
    metadata from ``auth_config``. Scopes / auth_url / access_type / prompt come
    from the resolved ``auth_config``.
    """
    _, user_profile = user_data
    await _assert_agent_oauth_admin(agent_id, user_profile)

    auth_config = await _resolve_tool_auth_config(tool_name)
    if not auth_config:
        raise HTTPException(status_code=404, detail="Tool not found")

    platform_tool = await _resolve_platform_tool_by_name(tool_name)
    if _is_mcp_oauth_config(auth_config, platform_tool):
        return await _start_mcp_oauth(tool_name, agent_id, auth_config)

    oauth_manager = get_oauth_manager()
    provider, token_url = oauth_manager.extract_oauth_config(auth_config)
    if not auth_config.get("auth_url") or not token_url:
        raise HTTPException(
            status_code=500,
            detail="OAuth authorization and token endpoints are not configured",
        )

    _validate_oauth_url(str(auth_config["auth_url"]), "authorization endpoint")
    _validate_oauth_url(str(token_url), "token endpoint")

    configured_auth_method = get_oauth_client_auth_method(auth_config)
    if not is_supported_oauth_client_auth_method(configured_auth_method):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "OAuth uses an unsupported token endpoint client authentication "
                f"method ({configured_auth_method}); manual reauthorization or "
                "a provider adapter is required"
            ),
        )

    client_metadata = _resolve_oauth_client_metadata(auth_config, provider)
    client_id = client_metadata["client_id"]
    redirect_uri = client_metadata["redirect_uri"]

    if not client_id or not redirect_uri:
        raise HTTPException(
            status_code=500,
            detail=(
                f"{provider.title()} OAuth client credentials are not configured. "
                "Set the provider environment variables or provide client_id "
                "and redirect_uri in the tool OAuth metadata."
            ),
        )

    _validate_oauth_url(redirect_uri, "redirect URI")
    pkce_supported = bool(auth_config.get("pkce_supported", True))
    verifier = secrets.token_urlsafe(64) if pkce_supported else ""
    state_data = {
        "oauth_flow": "native",
        "agent_id": str(agent_id),
        "tool_name": tool_name,
        "provider": str(provider),
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "token_url": str(token_url),
        "token_endpoint_auth_method": client_metadata["token_endpoint_auth_method"],
    }
    if verifier:
        state_data["code_verifier"] = verifier
    state = create_mcp_oauth_state(state_data)

    auth_url = build_mcp_authorization_url(
        str(auth_config["auth_url"]),
        client_id=client_id,
        redirect_uri=redirect_uri,
        state=state,
        code_challenge=pkce_challenge(verifier) if verifier else "",
        scopes=[str(scope) for scope in auth_config.get("scopes") or []],
    )

    # Add access_type and prompt if configured (required for refresh_token)
    extra_params: dict[str, str] = {}
    if auth_config.get("access_type"):
        extra_params["access_type"] = str(auth_config["access_type"])
    if auth_config.get("prompt"):
        extra_params["prompt"] = str(auth_config["prompt"])
    if extra_params:
        separator = "&" if "?" in auth_url else "?"
        auth_url = f"{auth_url}{separator}{urlencode(extra_params)}"
    return {"auth_url": auth_url}


@tool_router.get("/platform/{tool_id}/oauth")
@tracer.start_as_current_span("tool.routes.start_platform_mcp_oauth")
async def start_platform_mcp_oauth(
    tool_id: UUID,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Start a platform-admin-only OAuth flow for catalog discovery.

    The flow is deliberately separate from ``/auth/{tool_name}``, which
    creates an agent connection. Its callback uses the resulting token once to
    run ``tools/list`` and stores only public schemas on ``platform_tools``.
    No ``agent_tools`` row is created and no platform OAuth token is retained.
    """
    _, user_profile = user_data
    assert_platform_role(
        user_profile,
        "platform_admin",
        error_message="Only platform admins can discover MCP tools with OAuth",
    )
    tools, _ = await tool_service.get_platform_tools(
        only_active=False,
        include_drafts=True,
    )
    platform_tool = next((tool for tool in tools if tool.id == tool_id), None)
    if platform_tool is None or platform_tool.tool_source is not ToolSource.MCP:
        raise HTTPException(status_code=404, detail="MCP tool not found")
    auth_config = platform_tool.auth_config
    if not isinstance(auth_config, dict) or not _is_mcp_oauth_config(
        auth_config, platform_tool
    ):
        raise HTTPException(
            status_code=400,
            detail="Platform OAuth discovery requires an OAuth MCP configuration",
        )
    return await _start_mcp_oauth(
        platform_tool.name,
        None,
        auth_config,
        oauth_flow="mcp_platform",
        tool_id=tool_id,
    )


@tool_router.get("/callback")
async def oauth_callback(
    code: Optional[str] = None,
    state: str = "",
    error: Optional[str] = None,
    error_description: Optional[str] = None,
):
    """Validate an OAuth callback, exchange the code, and store encrypted tokens.

    All native and MCP flows use the same encrypted/authenticated, short-lived
    state. Unsigned legacy base64 state is intentionally rejected because it
    allowed a caller to rewrite the agent/tool target of an authorization grant.
    """
    if error:
        # Provider descriptions are user-controlled; keep the API response and
        # log record generic, never echoing a grant or provider detail.
        logger.info("OAuth authorization was denied by the provider")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OAuth authorization was denied or cancelled",
        )
    if not code or not state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OAuth callback is missing code or state",
        )

    try:
        decoded_state = decode_mcp_oauth_state(state)
        oauth_flow = str(decoded_state.get("oauth_flow") or "native")
        if oauth_flow not in {"native", "mcp", "mcp_platform"}:
            raise ValueError("Unsupported OAuth flow")
        tool_name = str(decoded_state["tool_name"])
        is_platform_discovery = oauth_flow == "mcp_platform"
        agent_id = (
            None if is_platform_discovery else UUID(str(decoded_state["agent_id"]))
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Invalid OAuth state") from None

    auth_config = await _resolve_tool_auth_config(tool_name)
    if not auth_config:
        raise HTTPException(status_code=404, detail="Tool not found")

    token_headers = {"Content-Type": "application/x-www-form-urlencoded"}
    if oauth_flow in {"mcp", "mcp_platform"}:
        token_url = str(
            decoded_state.get("token_url") or auth_config.get("token_url") or ""
        )
        client_id = str(
            decoded_state.get("client_id") or auth_config.get("client_id") or ""
        )
        redirect_uri = str(
            decoded_state.get("redirect_uri") or _mcp_oauth_redirect_uri(auth_config)
        )
        code_verifier = str(decoded_state.get("code_verifier") or "")
        if not code_verifier:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="MCP OAuth callback is missing PKCE verification state",
            )
        if not token_url or not client_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="MCP OAuth client metadata is incomplete",
            )
        token_endpoint_auth_method = str(
            decoded_state.get("token_endpoint_auth_method")
            or auth_config.get("token_endpoint_auth_method")
            or auth_config.get("client_auth_method")
            or ""
        ).lower()
        if not token_endpoint_auth_method:
            token_endpoint_auth_method = get_oauth_client_auth_method(auth_config) or ""
        if not is_supported_oauth_client_auth_method(token_endpoint_auth_method):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "MCP OAuth uses an unsupported token endpoint client "
                    f"authentication method ({token_endpoint_auth_method})"
                ),
            )
        stored_client_secret = await _resolve_stored_oauth_client_secret(tool_name)
        client_secret = stored_client_secret or os.getenv("MCP_OAUTH_CLIENT_SECRET", "")
        if not client_secret and token_endpoint_auth_method in {
            "client_secret_basic",
            "basic",
            "client_secret_post",
            "post",
        }:
            client_secret = await _resolve_stored_oauth_client_secret(tool_name) or ""
        oauth_data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": client_id,
            "code_verifier": code_verifier,
        }
        resource = str(
            decoded_state.get("resource") or auth_config.get("resource") or ""
        )
        if resource:
            oauth_data["resource"] = resource
        if token_endpoint_auth_method in {"client_secret_basic", "basic"}:
            if not client_secret:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="MCP OAuth client secret is not configured",
                )
            encoded_credentials = base64.b64encode(
                f"{client_id}:{client_secret}".encode()
            ).decode()
            token_headers["Authorization"] = f"Basic {encoded_credentials}"
            oauth_data.pop("client_id", None)
        elif token_endpoint_auth_method not in {"none", "public"} and client_secret:
            oauth_data["client_secret"] = client_secret
    else:
        oauth_manager = get_oauth_manager()
        provider, configured_token_url = oauth_manager.extract_oauth_config(auth_config)
        token_url = str(decoded_state.get("token_url") or configured_token_url or "")
        client_metadata = _resolve_oauth_client_metadata(auth_config, provider)
        client_id = str(decoded_state.get("client_id") or client_metadata["client_id"])
        redirect_uri = str(
            decoded_state.get("redirect_uri") or client_metadata["redirect_uri"]
        )
        stored_client_secret = await _resolve_stored_oauth_client_secret(tool_name)
        client_secret = stored_client_secret or client_metadata["client_secret"]
        if not token_url or not client_id or not redirect_uri:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(f"{str(provider).title()} OAuth client metadata is incomplete"),
            )
        token_endpoint_auth_method = str(
            decoded_state.get("token_endpoint_auth_method")
            or client_metadata["token_endpoint_auth_method"]
            or ""
        ).lower()
        if not token_endpoint_auth_method:
            token_endpoint_auth_method = get_oauth_client_auth_method(auth_config) or ""
        if not is_supported_oauth_client_auth_method(token_endpoint_auth_method):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "OAuth uses an unsupported token endpoint client "
                    f"authentication method ({token_endpoint_auth_method})"
                ),
            )
        oauth_data = {
            "code": code,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
            "client_id": client_id,
        }
        verifier = str(decoded_state.get("code_verifier") or "")
        if verifier:
            oauth_data["code_verifier"] = verifier
        if token_endpoint_auth_method in {"client_secret_basic", "basic"}:
            if not client_secret:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="OAuth client secret is not configured",
                )
            encoded_credentials = base64.b64encode(
                f"{client_id}:{client_secret}".encode()
            ).decode()
            token_headers["Authorization"] = f"Basic {encoded_credentials}"
            oauth_data.pop("client_id", None)
        elif token_endpoint_auth_method not in {"none", "public"} and client_secret:
            oauth_data["client_secret"] = client_secret

    _validate_oauth_url(token_url, "token endpoint")
    _validate_oauth_url(redirect_uri, "redirect URI")

    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(30.0), follow_redirects=False
        ) as client:
            response = await client.post(
                token_url, data=oauth_data, headers=token_headers
            )
            response.raise_for_status()
            token_data = response.json()
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "OAuth token exchange failed for %s with provider status %s",
            tool_name,
            exc.response.status_code,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="OAuth provider rejected the authorization code",
        ) from None
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "OAuth token exchange failed for %s (%s)", tool_name, type(exc).__name__
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="OAuth provider token exchange failed",
        ) from None

    if not isinstance(token_data, dict):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="OAuth provider returned an invalid token response",
        )
    access_token = token_data.get("access_token")
    if not isinstance(access_token, str) or not access_token:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="OAuth provider did not return an access token",
        )

    sensitive_config: dict[str, Any] = {
        "access_token": access_token,
        "expires_at": _oauth_expires_at(token_data.get("expires_in")),
    }
    if oauth_flow == "mcp":
        # DCR client IDs are public metadata, but keep them with the connection
        # so refresh works across backend instances without storing a secret.
        if decoded_state.get("client_id"):
            sensitive_config["oauth_client_id"] = decoded_state["client_id"]
        if decoded_state.get("resource"):
            sensitive_config["resource"] = decoded_state["resource"]
        if decoded_state.get("token_url"):
            sensitive_config["oauth_token_url"] = decoded_state["token_url"]
        if decoded_state.get("token_endpoint_auth_method"):
            sensitive_config["oauth_token_endpoint_auth_method"] = decoded_state[
                "token_endpoint_auth_method"
            ]
    refresh_token = token_data.get("refresh_token")
    if isinstance(refresh_token, str) and refresh_token.strip():
        sensitive_config["refresh_token"] = refresh_token
    else:
        logger.warning(
            "OAuth callback for %s returned no refresh token; manual "
            "reauthorization will be required when the access token expires",
            tool_name,
        )
    for safe_field in ("token_type", "scope"):
        if isinstance(token_data.get(safe_field), str):
            sensitive_config[safe_field] = token_data[safe_field]

    if is_platform_discovery:
        try:
            tool_count = await _discover_and_persist_mcp_tool_catalog(
                tool_name, access_token
            )
        except Exception as exc:
            logger.error(
                "Platform OAuth succeeded but catalog discovery failed for %s (%s)",
                tool_name,
                type(exc).__name__,
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="OAuth succeeded, but MCP catalog discovery failed",
            ) from None
        return {"message": "MCP tool catalog discovered", "tool_count": tool_count}

    if oauth_flow == "mcp":
        try:
            await _discover_and_persist_mcp_tool_catalog(tool_name, access_token)
        except Exception as exc:
            logger.warning(
                "Org OAuth succeeded but MCP catalog discovery failed for %s (%s)",
                tool_name,
                type(exc).__name__,
            )

    tools, _ = await tool_service.get_platform_tools(
        only_active=False, include_drafts=True
    )
    tool_id = next((tool.id for tool in tools if tool.name == tool_name), None)
    if not tool_id or agent_id is None:
        raise HTTPException(status_code=404, detail="Tool not found in DB")

    _, configure_error = await tool_service.configure_agent_tool(
        AgentToolCreate(
            agent_id=agent_id,
            tool_id=tool_id,
            sensitive_config=sensitive_config,
            is_enabled=True,
        )
    )
    if configure_error:
        logger.error(
            "OAuth succeeded for %s but encrypted connection storage failed",
            tool_name,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OAuth succeeded but the tool connection could not be saved",
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
    api_key: str = Body(
        ..., embed=True, description="API key to store in sensitive_config"
    ),
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Save or update API key in sensitive_config for a tool."""
    current_user_id, user_profile = user_data
    # CRIT: most dangerous endpoint — any logged-in user could otherwise
    # overwrite a real user's Google API key by guessing the agent_tool_id.
    await _assert_agent_tool_admin(agent_tool_id, user_profile)

    if not api_key or not api_key.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="API key cannot be empty"
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
