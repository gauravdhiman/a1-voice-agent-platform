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

from fastapi import APIRouter, Body, Depends, HTTPException, status
from opentelemetry import trace
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
)
from shared.voice_agents.tool_service import tool_service
from shared.voice_agents.tools.base.oauth_provider_utils import (
    get_oauth_manager,
)

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)
tool_router = APIRouter(prefix="/api/v1/tools", tags=["Tools"])


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


# Platform Tools (Admin only for write operations)
@tool_router.post(
    "/platform", response_model=PlatformTool, status_code=status.HTTP_201_CREATED
)
@tracer.start_as_current_span("tool.routes.create_platform_tool")
async def create_platform_tool(
    tool_data: PlatformToolCreate,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Create a new platform tool (Platform Admin only)."""
    current_user_id, user_profile = user_data
    assert_platform_role(
        user_profile, "platform_admin", error_message="Admin only"
    )

    tool, error = await tool_service.upsert_platform_tool(tool_data)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return tool


@tool_router.get("/platform", response_model=List[PlatformTool])
@tracer.start_as_current_span("tool.routes.get_platform_tools")
async def get_platform_tools(
    only_active: bool = True,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Get all platform tools."""
    tools, error = await tool_service.get_platform_tools(only_active)
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
    in-tree ``BaseTool`` subclass in the LiveKit registry) flow through the
    same OAuth start/callback endpoints as legacy tools. The DB row's
    ``auth_config`` is populated for legacy tools by
    ``LiveKitToolRegistry.sync_with_db`` and for MCP tools by the platform
    seed (see ``docs/03_implementation/mcp_integration_rfc.md``).

    Falls back to the legacy LiveKit registry for back-compat if no DB row
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
    tools, _ = await tool_service.get_platform_tools(only_active=False)
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
    from shared.voice_agents.tools.base.registry_livekit import livekit_tool_registry

    tool_class = livekit_tool_registry.get_tool_class(tool_name)
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
    (so MCP-sourced tools work), falling back to the legacy LiveKit registry.
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
    tools, _ = await tool_service.get_platform_tools(only_active=False)
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
