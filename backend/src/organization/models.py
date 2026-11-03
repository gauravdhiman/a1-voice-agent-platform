"""
Pydantic models for Organization functionality.
"""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from shared.organization.models import Organization  # noqa: F401
from shared.organization.models import (
    OrganizationCreate,
    OrganizationRuntime,
    OrganizationUpdate,
)


# Keep OrganizationEnhanced if it was used, but it seems redundant now
class OrganizationEnhanced(Organization):
    """Enhanced organization model with business details field."""

    pass


class PlatformOrganizationCreate(OrganizationCreate):
    """Organization fields plus the initial plan chosen by a platform admin."""

    plan_version_id: Optional[UUID] = None


class WebsiteBusinessContextRequest(BaseModel):
    """Request an unsaved business-context draft from a public website."""

    website: str = Field(
        min_length=8,
        max_length=2048,
        description="Public HTTP or HTTPS website URL to analyze",
    )


class WebsiteBusinessContextResponse(BaseModel):
    """Draft context and crawl coverage returned without modifying the organization."""

    business_details: str = Field(
        min_length=1,
        max_length=12000,
        description="Editable business-context draft grounded in fetched pages",
    )
    pages_analyzed: int = Field(
        ge=1,
        description="Number of public page excerpts included in the model request",
    )
    page_limit_reached: bool = Field(
        default=False,
        description="Whether discovery found more pages than the configured review limit",
    )
