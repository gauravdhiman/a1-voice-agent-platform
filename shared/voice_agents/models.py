"""
Pydantic models for Voice Agent functionality.
"""
from typing import Optional, Any
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime


class VoiceAgentBase(BaseModel):
    """Base model for Voice Agent."""
    name: str = Field(..., min_length=1, max_length=100, description="Agent name")
    phone_number: Optional[str] = Field(None, max_length=20, description="Twilio phone number")
    system_prompt: Optional[str] = Field(None, description="System prompt for the AI agent")
    is_active: bool = Field(default=True, description="Whether the agent is active")


class VoiceAgentCreate(VoiceAgentBase):
    """Model for creating a new voice agent."""
    organization_id: UUID = Field(..., description="Organization ID the agent belongs to")


class VoiceAgentUpdate(BaseModel):
    """Model for updating a voice agent."""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Agent name")
    phone_number: Optional[str] = Field(None, max_length=20, description="Twilio phone number")
    system_prompt: Optional[str] = Field(None, description="System prompt for the AI agent")
    is_active: Optional[bool] = Field(None, description="Whether the agent is active")


class VoiceAgent(VoiceAgentBase):
    """Model for a voice agent with all attributes."""
    id: UUID = Field(..., description="Agent ID")
    organization_id: UUID = Field(..., description="Organization ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
