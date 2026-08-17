"""Pydantic models for reusable voice-agent templates."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class VoiceTemplateBase(BaseModel):
    """Shared authoring fields for a reusable voice-agent template."""

    name: str = Field(..., min_length=1, max_length=100)
    industry: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    persona: Optional[str] = None
    tone: Optional[str] = None
    mission: Optional[str] = None
    greeting: Optional[str] = None
    custom_instructions: Optional[str] = None
    is_active: bool = True

    model_config = ConfigDict(extra="forbid")


class VoiceTemplateCreate(VoiceTemplateBase):
    """Payload for creating a platform-managed voice template."""


class VoiceTemplateUpdate(BaseModel):
    """Partial payload for updating a platform-managed voice template."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    industry: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    persona: Optional[str] = None
    tone: Optional[str] = None
    mission: Optional[str] = None
    greeting: Optional[str] = None
    custom_instructions: Optional[str] = None
    is_active: Optional[bool] = None

    model_config = ConfigDict(extra="forbid")


class VoiceTemplate(VoiceTemplateBase):
    """Persisted voice template returned by public and admin APIs."""

    id: UUID
    created_at: datetime
    updated_at: datetime
