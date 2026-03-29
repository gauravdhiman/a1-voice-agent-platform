"""Pydantic models for voice templates."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class VoiceTemplate(BaseModel):
    id: UUID
    name: str
    industry: str
    description: Optional[str] = None
    persona: Optional[str] = None
    tone: Optional[str] = None
    mission: Optional[str] = None
    greeting: Optional[str] = None
    custom_instructions: Optional[str] = None
    is_active: bool = True
    created_at: datetime
    updated_at: datetime
