"""Default organization provisioning for newly authenticated users."""

from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from opentelemetry import trace

from src.organization.models import OrganizationCreate
from src.organization.service import organization_service
from src.rbac.roles.service import role_service
from src.rbac.user_roles.models import UserRoleCreate
from src.rbac.user_roles.service import user_role_service

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


def _user_has_organization(user_id: UUID) -> bool:
    """Return True when the user already belongs to at least one organization."""
    response = (
        organization_service.supabase.table("user_roles")
        .select("id")
        .eq("user_id", str(user_id))
        .not_.is_("organization_id", "null")
        .limit(1)
        .execute()
    )
    return bool(response.data)


@tracer.start_as_current_span("organization.ensure_default_organization_for_user")
async def ensure_default_organization_for_user(
    user_id: UUID,
    email: str,
    *,
    organization_name: Optional[str] = None,
) -> tuple[Optional[UUID], Optional[str]]:
    """Create a default organization and org_admin role when the user has none.

    Email/password signup and OAuth flows (LinkedIn, future providers) call this
    helper so first-time users land in the product with a tenant already created,
    matching the legacy signup behavior.

    Args:
        user_id: Supabase auth user identifier.
        email: Verified email used for the default organization label.
        organization_name: Optional override for the organization display name.

    Returns:
        Tuple of organization UUID and optional error message. When the user
        already has an organization, returns ``(None, None)``.
    """
    current_span = trace.get_current_span()
    current_span.set_attribute("user.id", str(user_id))

    if _user_has_organization(user_id):
        current_span.add_event("default_organization_already_present")
        return None, None

    org_admin_role, role_error = await role_service.get_role_by_name("org_admin")
    if role_error or not org_admin_role:
        message = f"Could not find org_admin role: {role_error}"
        logger.warning(message)
        current_span.set_status(trace.Status(trace.StatusCode.ERROR, message))
        return None, message

    org_data = OrganizationCreate(
        name=organization_name or f"{email}'s Organization",
        description=(
            f"Default organization for {email}. "
            "Please update with your organization details."
        ),
        slug=f"{str(user_id).replace('-', '')[:8]}-dummy-org",
        is_active=True,
    )

    organization, org_error = await organization_service.create_organization(org_data)
    if org_error or not organization:
        message = org_error or "Failed to create default organization"
        logger.warning("Default organization provisioning failed: %s", message)
        current_span.set_status(trace.Status(trace.StatusCode.ERROR, message))
        return None, message

    user_role_data = UserRoleCreate(
        user_id=user_id,
        role_id=org_admin_role.id,
        organization_id=organization.id,
    )
    _, role_assign_error = await user_role_service.assign_role_to_user(user_role_data)
    if role_assign_error:
        message = f"Could not assign org_admin role: {role_assign_error}"
        logger.warning(message)
        current_span.set_status(trace.Status(trace.StatusCode.ERROR, message))
        return organization.id, message

    current_span.set_attribute("organization.id", str(organization.id))
    current_span.set_status(trace.Status(trace.StatusCode.OK))
    logger.info(
        "Provisioned default organization %s for user %s",
        organization.id,
        user_id,
    )
    return organization.id, None
