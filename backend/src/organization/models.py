"""
Pydantic models for Organization functionality.
"""

from shared.organization.models import (
    Organization,
    OrganizationBase,
    OrganizationCreate,
    OrganizationUpdate,
)

# Keep OrganizationEnhanced if it was used, but it seems redundant now
class OrganizationEnhanced(Organization):
    """Enhanced organization model with business details field."""
    pass
