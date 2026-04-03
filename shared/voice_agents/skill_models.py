"""
Pydantic models for the Skills system.

Skills are reusable knowledge/procedure packages (markdown) that can be
assigned to agents. They use progressive disclosure — only metadata is
loaded in the system prompt; full content is loaded on-demand via tool call.
"""

import re
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class OrganizationSkillBase(BaseModel):
    """Base model for organization skills."""

    name: str = Field(..., min_length=1, max_length=200, description="Skill display name")
    slug: str = Field(..., min_length=1, max_length=100, description="URL-safe unique identifier")
    description: Optional[str] = Field(None, description="Short description for skill selection UI and prompt metadata")
    content: str = Field(..., min_length=1, description="Full skill content in markdown (SKILL.md)")
    category: str = Field(default="custom", description="Skill category: 'built_in' or 'custom'")
    is_active: bool = Field(default=True, description="Whether the skill is active")
    version: Optional[str] = Field(None, max_length=50, description="Skill version (e.g., '1.0.0')")
    author: Optional[str] = Field(None, max_length=200, description="Skill author or source attribution")
    content_hash: Optional[str] = Field(None, max_length=64, description="SHA-256 hash of content for change detection")
    source_url: Optional[str] = Field(None, description="Source URL for imported skills (GitHub, skills.sh)")
    source_ref: Optional[str] = Field(None, description="Source version reference (commit hash, tag)")

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        """Validate slug is URL-safe kebab-case."""
        if not re.match(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", v):
            raise ValueError(
                "Slug must be lowercase kebab-case (e.g., 'appointment-booking')"
            )
        return v

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        """Validate category is one of allowed values."""
        allowed = {"built_in", "custom"}
        if v not in allowed:
            raise ValueError(f"Category must be one of: {', '.join(allowed)}")
        return v


class OrganizationSkillCreate(OrganizationSkillBase):
    """Model for creating a new skill."""

    organization_id: UUID = Field(..., description="Organization ID")


class OrganizationSkillUpdate(BaseModel):
    """Model for updating a skill. All fields optional."""

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    content: Optional[str] = Field(None, min_length=1)
    is_active: Optional[bool] = None


class OrganizationSkill(OrganizationSkillBase):
    """Full skill model with all attributes."""

    id: UUID = Field(..., description="Skill ID")
    organization_id: UUID = Field(..., description="Organization ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class OrganizationSkillSummary(BaseModel):
    """Lightweight skill summary for prompt injection and list views."""

    slug: str
    name: str
    description: Optional[str]


class AgentSkillAssignment(BaseModel):
    """Model for assigning a skill to an agent."""

    skill_id: UUID = Field(..., description="Skill ID to assign")


class AgentSkillResponse(BaseModel):
    """Response model for an agent's assigned skill."""

    id: UUID
    agent_id: UUID
    skill_id: UUID
    skill: OrganizationSkill
    is_active: bool
    created_at: datetime


class SkillFileResponse(BaseModel):
    """Response model for a skill reference file (Phase 2b)."""

    id: UUID
    skill_id: UUID
    file_path: str
    content: str
    file_kind: str
    created_at: datetime
    updated_at: datetime
