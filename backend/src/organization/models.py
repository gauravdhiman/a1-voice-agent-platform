"""
Pydantic models for Organization functionality.
"""

from typing import Optional
from uuid import UUID

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
