"""
Pydantic models for the /me permission resolution contract.

The response model on `GET /me` is `UserProfile`. This module defines the
permission map embedded in that response and the canonical list of resources
and actions the frontend can rely on. Adding a new resource/action requires:

1. Adding it to `ResourceName` / `ActionName` (or `*`).
2. Wiring the resolver in `permissions_service.resolve_permissions` to
   grant it for the right roles.
3. Updating the frontend `nav-config.ts` and the `useHasPermission` callsite
   that gates the corresponding nav item or page action.
"""
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


# Canonical resources and actions in the contract.
# Frontend and backend both import from this file (via /me response) and
# validate against it.
RESOURCE_NAMES: tuple[str, ...] = (
    "agent",
    "phone_number",
    "skill",
    "call_log",
    "member",
    "billing",
    "organization",
    "platform",
    "*",  # wildcard
)


class ResourcePermissions(BaseModel):
    """Map of resource name -> list of action strings.

    Example: {"agent": ["read", "write"], "billing": ["manage"]}
    An empty dict means "no permissions granted" (e.g. user has no org).
    A wildcard is encoded as {"*": ["*"]}.
    """

    # Using Dict[str, list[str]] is intentional: it matches the contract the
    # frontend `useHasPermission` hook consumes. The full set of resources
    # is enforced by the resolver, not the schema.
    permissions: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Map of resource name to list of action names. '*' is the wildcard.",
    )


class MyPermissions(BaseModel):
    """Permissions attached to the current user for the current org context.

    This is the value the resolver returns and the /me endpoint embeds in
    `UserProfile.permissions`. The frontend hook reads this directly.
    """

    current_organization_id: Optional[UUID] = Field(
        None,
        description=(
            "Organization the permissions are scoped to. None when the user "
            "has no current org (or platform-admin context)."
        ),
    )
    permissions: dict[str, list[str]] = Field(
        default_factory=dict,
        description=(
            "Resource -> actions map. '*' key with '*' value is the wildcard "
            "granted to platform admins."
        ),
    )
