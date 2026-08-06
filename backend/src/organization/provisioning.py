"""Organization provisioning for newly authenticated users without a tenant."""

from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from opentelemetry import trace

from shared.organization.slug_utils import (
    suggest_organization_slug_from_name,
    validate_organization_slug,
)
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


def _is_slug_taken(slug: str) -> bool:
    """Return True when another organization already uses ``slug``."""
    response = (
        organization_service.supabase.table("organizations")
        .select("id")
        .eq("slug", slug)
        .limit(1)
        .execute()
    )
    return bool(response.data)


def _unique_slug_from_name(name: str, user_id: UUID) -> str:
    """Build a unique kebab-case slug from an organization name.

    Uses the organization name as the primary slug source. On collision,
    appends a short user-id suffix (and a numeric counter if needed).
    """
    base = suggest_organization_slug_from_name(name)
    if not base:
        base = "organization"

    is_valid, _ = validate_organization_slug(base)
    if not is_valid:
        base = "organization"

    if not _is_slug_taken(base):
        return base

    suffix = str(user_id).replace("-", "")[:6]
    candidate = f"{base}-{suffix}"
    attempt = 2
    while _is_slug_taken(candidate):
        candidate = f"{base}-{suffix}{attempt}"
        attempt += 1
        if attempt > 50:
            # Extremely unlikely; fall back to a fully unique slug.
            return f"{base}-{str(user_id).replace('-', '')[:12]}"
    return candidate


@tracer.start_as_current_span("organization.ensure_default_organization_for_user")
async def ensure_default_organization_for_user(
    user_id: UUID,
    email: str,
    *,
    organization_name: Optional[str] = None,
) -> tuple[Optional[UUID], Optional[str]]:
    """Create a normal organization and org_admin role when the user has none.

    Email/password signup and OAuth flows call this helper so first-time users
    land in the product with a tenant already created. Invited users should
    already have membership from invitation processing, so this becomes a no-op.

    Args:
        user_id: Supabase auth user identifier.
        email: Verified email used when deriving a default organization name.
        organization_name: Optional override for the organization display name.

    Returns:
        Tuple of organization UUID and optional error message. When the user
        already has an organization, returns ``(None, None)``.
    """
    current_span = trace.get_current_span()
    current_span.set_attribute("user.id", str(user_id))

    if _user_has_organization(user_id):
        current_span.add_event("organization_already_present")
        return None, None

    org_admin_role, role_error = await role_service.get_role_by_name("org_admin")
    if role_error or not org_admin_role:
        message = f"Could not find org_admin role: {role_error}"
        logger.warning(message)
        current_span.set_status(trace.Status(trace.StatusCode.ERROR, message))
        return None, message

    name = organization_name or f"{email}'s Organization"
    slug = _unique_slug_from_name(name, user_id)

    org_data = OrganizationCreate(
        name=name,
        description=None,
        slug=slug,
        is_active=True,
    )

    organization, org_error = await organization_service.create_organization(org_data)
    if org_error or not organization:
        message = org_error or "Failed to create organization"
        logger.warning("Organization provisioning failed: %s", message)
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
    current_span.set_attribute("organization.slug", slug)
    current_span.set_status(trace.Status(trace.StatusCode.OK))
    logger.info(
        "Provisioned organization %s (slug=%s) for user %s",
        organization.id,
        slug,
        user_id,
    )
    return organization.id, None
