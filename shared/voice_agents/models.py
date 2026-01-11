"""
Pydantic models for Voice Agent functionality.
"""

import re
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class VoiceAgentBase(BaseModel):
    """Base model for Voice Agent."""

    name: str = Field(..., min_length=1, max_length=100, description="Agent name")
    phone_number: str = Field(..., max_length=20, description="Twilio phone number")
    system_prompt: str = Field(
        ..., min_length=1, description="System prompt for AI agent"
    )
    is_active: bool = Field(default=True, description="Whether the agent is active")

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, v: str) -> str:
        """Validate E.164 phone number format."""
        # E.164 format requires country code (1-3 digits) + subscriber number
        # Minimum 8 characters total (including +) for valid international numbers
        if not re.match(r"^\+[1-9]\d{7,14}$", v):
            raise ValueError(
                "Phone number must be in E.164 format "
                "with at least 8 digits "
                "(e.g., +14155551234 or +441632960000)"
            )
        return v


class VoiceAgentCreate(VoiceAgentBase):
    """Model for creating a new voice agent."""

    organization_id: UUID = Field(
        ..., description="Organization ID that agent belongs to"
    )


class VoiceAgentUpdate(BaseModel):
    """Model for updating a voice agent."""

    name: Optional[str] = Field(
        None, min_length=1, max_length=100, description="Agent name"
    )
    phone_number: Optional[str] = Field(
        None, max_length=20, description="Twilio phone number"
    )
    system_prompt: Optional[str] = Field(
        None, min_length=1, description="System prompt for AI agent"
    )
    is_active: Optional[bool] = Field(None, description="Whether the agent is active")


class VoiceAgent(VoiceAgentBase):
    """Model for a voice agent with all attributes."""

    id: UUID = Field(..., description="Agent ID")
    organization_id: UUID = Field(..., description="Organization ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class DeleteResponse(BaseModel):
    """Response model for delete operations."""

    id: UUID = Field(..., description="ID of deleted resource")
    success: bool = Field(..., description="Whether deletion was successful")
