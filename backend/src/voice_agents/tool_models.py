"""
Pydantic models for Platform Tool functionality.
"""
from typing import Optional, Any, Dict
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime


class PlatformToolBase(BaseModel):
    """Base model for Platform Tool."""
    name: str = Field(..., min_length=1, max_length=100, description="Tool name")
    description: Optional[str] = Field(None, description="Tool description")
    config_schema: Optional[Dict[str, Any]] = Field(None, description="JSON schema for tool configuration")
    is_active: bool = Field(default=True, description="Whether the tool is available for use")


class PlatformToolCreate(PlatformToolBase):
    """Model for creating a new platform tool."""
    pass


class PlatformToolUpdate(BaseModel):
    """Model for updating a platform tool."""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Tool name")
    description: Optional[str] = Field(None, description="Tool description")
    config_schema: Optional[Dict[str, Any]] = Field(None, description="JSON schema for tool configuration")
    is_active: Optional[bool] = Field(None, description="Whether the tool is available for use")


class PlatformTool(PlatformToolBase):
    """Model for a platform tool with all attributes."""
    id: UUID = Field(..., description="Tool ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class AgentToolBase(BaseModel):
    """Base model for Agent Tool configuration."""
    agent_id: UUID = Field(..., description="Agent ID")
    tool_id: UUID = Field(..., description="Tool ID")
    config: Optional[Dict[str, Any]] = Field(None, description="Public tool configuration for this agent")
    sensitive_config: Optional[Dict[str, Any]] = Field(None, description="Sensitive tool configuration (will be encrypted), example auth token, refresh token etc.")
    is_enabled: bool = Field(default=True, description="Whether the tool is enabled for this agent")


class AgentToolCreate(AgentToolBase):
    """Model for configuring a tool for an agent."""
    pass


class AgentToolUpdate(BaseModel):
    """Model for updating an agent tool configuration."""
    config: Optional[Dict[str, Any]] = Field(None, description="Public tool configuration for this agent")
    sensitive_config: Optional[Dict[str, Any]] = Field(None, description="Sensitive tool configuration (will be encrypted)")
    is_enabled: Optional[bool] = Field(None, description="Whether the tool is enabled for this agent")


class AgentTool(AgentToolBase):
    """Model for an agent tool with all attributes."""
    id: UUID = Field(..., description="Agent tool configuration ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    tool: Optional[PlatformTool] = Field(None, description="Tool details")
