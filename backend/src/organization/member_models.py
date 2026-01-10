"""
Pydantic models for organization member data.
"""

from typing import List
from uuid import UUID

from pydantic import BaseModel, Field


class MemberRole(BaseModel):
    """Role information for a member."""

    id: UUID = Field(..., description="Role ID")
    name: str = Field(..., description="Role name")
    description: str = Field(..., description="Role description")


class OrganizationMember(BaseModel):
    """Organization member with role information."""

    id: UUID = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    first_name: str = Field(..., description="User first name")
    last_name: str = Field(..., description="User last name")
    is_verified: bool = Field(..., description="Whether user email is verified")
    created_at: str = Field(..., description="Account creation timestamp")
    roles: List[MemberRole] = Field(
        default=[], description="User's roles in this organization"
    )
