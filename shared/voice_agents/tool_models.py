"""
Pydantic models for Platform Tool functionality.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class AuthStatus(str, Enum):
    """Authentication status for a tool."""

    NOT_AUTHENTICATED = "not_authenticated"  # No tokens exist
    AUTHENTICATED = "authenticated"  # Valid tokens exist
    EXPIRED = "expired"  # Tokens exist but have expired


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
    auth_config: Optional[Dict[str, Any]] = Field(
        None, description="Authentication config (OAuth URLs, scopes, provider)"
    )
    is_active: bool = Field(
        default=True, description="Whether is tool available for use"
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


class AgentTool(AgentToolBase):
    """Model for an agent tool with all attributes (internal use)."""

    id: UUID = Field(..., description="Agent tool configuration ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
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
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    tool: Optional[PlatformTool] = Field(None, description="Tool details")
