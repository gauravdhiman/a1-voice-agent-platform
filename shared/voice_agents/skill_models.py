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


# ═══════════════════════════════════════════════════════════════════════════════
# PLATFORM SKILL MODELS (Immutable templates controlled by platform)
# ═══════════════════════════════════════════════════════════════════════════════

class PlatformSkillBase(BaseModel):
    """Base model for platform-level skill templates."""

    slug: str = Field(..., min_length=1, max_length=100, description="URL-safe unique identifier (global)")
    name: str = Field(..., min_length=1, max_length=200, description="Skill display name")
    description: Optional[str] = Field(None, description="Short description for skill selection UI")
    content: str = Field(..., min_length=1, description="Full skill content in markdown (SKILL.md)")
    version: str = Field(default="1970.01.01_1", description="Date-based version (YYYY.MM.DD_N)")
    content_hash: Optional[str] = Field(None, max_length=64, description="SHA-256 hash of content")
    is_active: bool = Field(default=True, description="Platform-level visibility")
    author: Optional[str] = Field(None, max_length=200, description="Attribution (e.g., 'Platform', 'John Doe')")

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        """Validate slug is URL-safe kebab-case."""
        if not re.match(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", v):
            raise ValueError("Slug must be lowercase kebab-case (e.g., 'appointment-booking')")
        return v

    @field_validator("version")
    @classmethod
    def validate_version(cls, v: str) -> str:
        """Validate version follows YYYY.MM.DD_N format."""
        if not re.match(r"^\d{4}\.\d{2}\.\d{2}_\d+$", v):
            raise ValueError("Version must be YYYY.MM.DD_N (e.g., '2026.05.03_1')")
        return v


class PlatformSkillCreate(PlatformSkillBase):
    """Model for creating a new platform skill."""
    pass


class PlatformSkillUpdate(BaseModel):
    """Model for updating a platform skill. Bumps version automatically."""

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    content: Optional[str] = Field(None, min_length=1)
    is_active: Optional[bool] = None


class PlatformSkill(PlatformSkillBase):
    """Full platform skill model with all attributes."""

    id: UUID = Field(..., description="Skill ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class PlatformSkillSummary(BaseModel):
    """Lightweight summary for template browsing.

    Includes ``is_active`` so platform admins can see and manage deprecated
    (hidden) skills. For non-admin browsing the value is always ``True`` since
    inactive skills are filtered out server-side.
    """

    id: UUID
    slug: str
    name: str
    description: Optional[str]
    version: str
    is_active: bool = True


class PlatformSkillFileCreate(BaseModel):
    """Model for creating a reference file within a platform skill."""

    file_path: str = Field(..., min_length=1, description="File path within skill")
    content: str = Field(..., min_length=1, description="File content")
    file_kind: str = Field(default="reference", description="File kind")

    @field_validator("file_kind")
    @classmethod
    def validate_file_kind(cls, v: str) -> str:
        allowed = {"reference", "script", "asset", "other"}
        if v not in allowed:
            raise ValueError(f"File kind must be one of: {', '.join(allowed)}")
        return v


class PlatformSkillFile(BaseModel):
    """Full response model for a platform skill reference file."""

    id: UUID
    skill_id: UUID
    file_path: str
    content: str
    file_kind: str
    content_hash: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class PlatformSkillFileSummary(BaseModel):
    """Lightweight file summary (no content) for file tree listings."""

    id: UUID
    file_path: str
    file_kind: str
    content_hash: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════════════
# ORGANIZATION SKILL MODELS (Editable copies owned by orgs)
# ═══════════════════════════════════════════════════════════════════════════════

class OrganizationSkillBase(BaseModel):
    """Base model for organization skills."""

    name: str = Field(..., min_length=1, max_length=200, description="Skill display name")
    slug: str = Field(..., min_length=1, max_length=100, description="URL-safe unique identifier (org-level)")
    description: Optional[str] = Field(None, description="Short description for skill selection UI and prompt metadata")
    content: str = Field(..., min_length=1, description="Full skill content in markdown (SKILL.md)")
    # category is always "custom" for org skills — some are forked, some created, some imported
    version: Optional[str] = Field(None, max_length=50, description="Skill version (e.g., '1.0.0')")
    author: Optional[str] = Field(None, max_length=200, description="Skill author or source attribution")
    content_hash: Optional[str] = Field(None, max_length=64, description="SHA-256 hash of content for change detection")
    is_active: bool = Field(default=True, description="Whether skill is active and available for assignment")
    # Fork model fields
    source_skill_id: Optional[UUID] = Field(None, description="FK to platform_skills.id if forked; null if created/imported")
    source_version: Optional[str] = Field(None, max_length=20, description="Platform skill version at time of fork")
    is_visible: bool = Field(default=True, description="Whether skill appears in org library for assignment")

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        """Validate slug is URL-safe kebab-case."""
        if not re.match(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", v):
            raise ValueError("Slug must be lowercase kebab-case (e.g., 'appointment-booking')")
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
    is_visible: Optional[bool] = None


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
    is_active: bool = True


# ═══════════════════════════════════════════════════════════════════════════════
# FORK/REFRESH REQUEST MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class SkillForkRequest(BaseModel):
    """Request to fork a platform skill into an org library."""

    platform_skill_id: UUID = Field(..., description="ID of the platform skill to fork")
    custom_name: Optional[str] = Field(None, min_length=1, max_length=200, description="Optional custom name for the fork")
    custom_slug: Optional[str] = Field(None, min_length=1, max_length=100, description="Optional custom slug (auto-generated if not provided)")

    @field_validator("custom_slug")
    @classmethod
    def validate_custom_slug(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not re.match(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", v):
            raise ValueError("Slug must be lowercase kebab-case")
        return v


class SkillRefreshRequest(BaseModel):
    """Request to refresh a forked skill from its platform source."""

    confirm_overwrite: bool = Field(..., description="Must be true to accept full bundle replacement")


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT SKILL ASSIGNMENT MODELS
# ═══════════════════════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════════════════════
# SKILL FILE MODELS (Reference files within org skills)
# ═══════════════════════════════════════════════════════════════════════════════

class SkillFileCreate(BaseModel):
    """Model for creating a reference file within a skill."""

    file_path: str = Field(..., min_length=1, description="File path within skill (e.g., 'references/policies.md')")
    content: str = Field(..., min_length=1, description="File content")
    file_kind: str = Field(default="reference", description="File kind: 'reference', 'script', 'asset', 'other'")

    @field_validator("file_kind")
    @classmethod
    def validate_file_kind(cls, v: str) -> str:
        allowed = {"reference", "script", "asset", "other"}
        if v not in allowed:
            raise ValueError(f"File kind must be one of: {', '.join(allowed)}")
        return v


class SkillFileUpdate(BaseModel):
    """Model for updating a reference file."""

    file_path: Optional[str] = Field(None, min_length=1, description="New file path (for renaming/moving)")
    content: Optional[str] = Field(None, min_length=1)


class SkillFile(BaseModel):
    """Full response model for a skill reference file."""

    id: UUID
    skill_id: UUID
    file_path: str
    content: str
    file_kind: str
    content_hash: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class SkillFileSummary(BaseModel):
    """Lightweight file summary (no content) for file tree listings."""

    id: UUID
    file_path: str
    file_kind: str
    content_hash: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════════════
# IMPORT MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class SkillImportRequest(BaseModel):
    """Request model for importing a skill from an external URL."""

    url: str = Field(..., min_length=1, description="GitHub URL or skills.sh URL")


class SkillImportResult(BaseModel):
    """Result of a skill import operation (organization skill)."""

    skill: OrganizationSkill
    files_imported: int
    source_url: str


class PlatformSkillImportResult(BaseModel):
    """Result of importing an external skill as a platform skill template.

    Platform admins import skills from external marketplaces/GitHub; the
    imported package becomes a platform-level template (not an org custom skill).
    """

    skill: PlatformSkill
    files_imported: int
    source_url: str


# ═══════════════════════════════════════════════════════════════════════════════
# UPDATE LOG MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class SkillUpdateLog(BaseModel):
    """Audit log entry for skill refresh operations."""

    id: UUID
    org_skill_id: UUID
    old_source_version: Optional[str]
    new_source_version: Optional[str]
    performed_by: Optional[UUID]
    performed_at: datetime
