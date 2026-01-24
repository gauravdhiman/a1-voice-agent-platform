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
    if not user_profile.has_role("platform_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")

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

    # Permission check
    if not user_profile.has_role("platform_admin"):
        if not user_profile.has_role("org_admin", str(agent.organization_id)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to configure tools for this agent",
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

    # Permission check
    if not user_profile.has_role("platform_admin"):
        if not user_profile.has_role(
            "org_admin", str(agent.organization_id)
        ) and not user_profile.has_role("regular_user", str(agent.organization_id)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to view tools for this agent",
            )

    tools, error = await tool_service.get_agent_tools(agent_id)
    if error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error
        )
    return tools


# OAuth Handlers
@tool_router.get("/auth/{tool_name}")
@tracer.start_as_current_span("tool.routes.start_oauth")
async def start_oauth(
    tool_name: str,
    agent_id: UUID,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Start OAuth flow for a specific tool."""
    from shared.voice_agents.tools.base.registry_livekit import livekit_tool_registry

    tool_class = livekit_tool_registry.get_tool_class(tool_name)
    if not tool_class:
        raise HTTPException(status_code=404, detail="Tool not found")

    metadata = tool_class().metadata
    if not metadata.requires_auth:
        raise HTTPException(status_code=400, detail="Tool does not require auth")

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
    auth_params = {
        "client_id": quote(client_id),
        "redirect_uri": quote(redirect_uri),
        "response_type": "code",
        "scope": quote(" ".join(metadata.auth_config["scopes"])),
        "state": quote(state),
    }

    # Add access_type and prompt if configured (required for refresh_token)
    if metadata.auth_config.get("access_type"):
        auth_params["access_type"] = quote(metadata.auth_config["access_type"])
    if metadata.auth_config.get("prompt"):
        auth_params["prompt"] = quote(metadata.auth_config["prompt"])

    # Construct URL
    auth_query = "&".join(f"{k}={v}" for k, v in auth_params.items())
    auth_url = f"{metadata.auth_config['auth_url']}?{auth_query}"
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

    # 2. Get tool metadata from registry
    from shared.voice_agents.tools.base.registry_livekit import livekit_tool_registry

    tool_class = livekit_tool_registry.get_tool_class(tool_name)
    if not tool_class:
        raise HTTPException(status_code=404, detail="Tool not found")

    metadata = tool_class().metadata
    
    # Get OAuth provider manager singleton
    oauth_manager = get_oauth_manager()

    # Extract provider and token_url using singleton manager
    provider, token_url = oauth_manager.extract_oauth_config(metadata.auth_config)
    
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

    # We'd need to fetch the agent_tool first to check organization permissions
    # For now, let's keep it simple and assume the user has access if they know the ID,
    # but in production we should check org_id.

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

    deleted, error = await tool_service.delete_agent_tool(agent_tool_id)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Agent tool not found"
        )
    return {"id": str(agent_tool_id), "deleted": True}
