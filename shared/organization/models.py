"""
Pydantic models for Organization functionality shared across backend and worker.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class OrganizationBase(BaseModel):
    """Base model for Organization."""

    name: str = Field(
        ..., min_length=1, max_length=100, description="Organization name"
    )
    description: Optional[str] = Field(
        None, max_length=500, description="Organization description"
    )
    slug: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Organization slug (unique identifier)",
    )
    website: Optional[str] = Field(None, description="Organization website URL")
    is_active: bool = Field(
        default=True, description="Whether the organization is active"
    )
    industry: Optional[str] = Field(
        None, max_length=100, description="Industry of the organization"
    )
    location: Optional[str] = Field(
        None, max_length=255, description="Physical address or location"
    )
    business_details: Optional[str] = Field(
        None,
        description="""
        Comprehensive business context for AI agent system prompts.
        
        Include information such as:
        - Products and services offered
        - Business hours (including special schedules, holidays, seasonal variations)
        - Service areas and location details
        - Company policies and procedures
        - Unique selling points and differentiators
        - Common customer questions and how to handle them
        - Emergency or after-hours protocols
        - Any other context that helps the AI represent your business accurately
        
        This information is used to construct the AI agent's system prompt
        and will be referenced when interacting with callers.
        """,
    )


class OrganizationCreate(OrganizationBase):
    """Model for creating a new organization."""

    pass


class OrganizationUpdate(BaseModel):
    """Model for updating an organization."""

    name: Optional[str] = Field(
        None, min_length=1, max_length=100, description="Organization name"
    )
    description: Optional[str] = Field(
        None, max_length=500, description="Organization description"
    )
    slug: Optional[str] = Field(
        None,
        min_length=1,
        max_length=100,
        description="Organization slug (unique identifier)",
    )
    website: Optional[str] = Field(None, description="Organization website URL")
    is_active: Optional[bool] = Field(
        None, description="Whether the organization is active"
    )
    industry: Optional[str] = Field(
        None, max_length=100, description="Industry of the organization"
    )
    location: Optional[str] = Field(
        None, max_length=255, description="Physical address or location"
    )
    business_details: Optional[str] = Field(
        None,
        description="""
        Comprehensive business context for AI agent system prompts.
        
        Include information such as:
        - Products and services offered
        - Business hours (including special schedules, holidays, seasonal variations)
        - Service areas and location details
        - Company policies and procedures
        - Unique selling points and differentiators
        - Common customer questions and how to handle them
        - Emergency or after-hours protocols
        - Any other context that helps the AI represent your business accurately
        
        This information is used to construct the AI agent's system prompt
        and will be referenced when interacting with callers.
        """,
    )


class Organization(OrganizationBase):
    """Model for an organization with all attributes."""

    id: UUID = Field(..., description="Organization ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
