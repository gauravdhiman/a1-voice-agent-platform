"""
Service for resolving a user's effective permissions on the current org.

This is the Phase 1 stub resolver: it walks the user's roles + the explicit
permissions already attached to those roles, and applies the contract from
`docs/tw-drafts/navigation-redesign.md` Section 5.1.

Phase 2 will replace the body of `resolve_permissions` with a real lookup
against the `role_permissions` table joined with `user_roles` for the
current org. The function signature and the `MyPermissions` return shape
are stable; downstream code (the /me route, the frontend hook) does not
change.
"""
from typing import Optional
from uuid import UUID

from opentelemetry import trace

from src.auth.models import UserProfile
from src.auth.permissions_models import MyPermissions

# Tracer for this module
tracer = trace.get_tracer(__name__)


# --- Contract constants (mirror docs/tw-drafts/navigation-redesign.md) ---

# Platform admin = full wildcard. The frontend hook treats {"*": ["*"]} as
# "every resource, every action".
PLATFORM_ADMIN_ROLE = "platform_admin"
ORG_ADMIN_ROLE = "org_admin"
WILDCARD_RESOURCE = "*"
WILDCARD_ACTION = "*"


def _is_platform_admin(user: UserProfile) -> bool:
    """A platform admin has a platform_admin role with no organization_id."""
    return any(
        ur.role.name == PLATFORM_ADMIN_ROLE and ur.organization_id is None
        for ur in user.roles
    )


def _has_org_admin_on(user: UserProfile, org_id: UUID) -> bool:
    """The user has org_admin on the given organization_id.

    Kept as a public-ish helper for callers (e.g. future route-level
    admin checks); the resolver itself uses `_actions_from_role` directly
    because it needs the full permission set, not a boolean.
    """
    return any(
        ur.role.name == ORG_ADMIN_ROLE and ur.organization_id == org_id
        for ur in user.roles
    )


def _is_member_of(user: UserProfile, org_id: UUID) -> bool:
    """The user has any role on the given organization_id (member, org_admin, etc.)."""
    return any(ur.organization_id == org_id for ur in user.roles)


def _actions_from_role(user: UserProfile, org_id: Optional[UUID]) -> set[str]:
    """Collect the set of permission strings the user has on the given org.

    Mirrors `UserProfile.has_permission` semantics: only permissions whose
    containing role is scoped to org_id are counted. The caller is
    responsible for the platform-admin short-circuit and the no-org
    short-circuit; this helper assumes org_id is a real organization and
    the user is NOT a platform admin.

    Args:
        user: The user profile (must NOT be a platform admin, must have a
            current org context).
        org_id: The current organization the permissions are scoped to.

    Returns:
        The set of `<resource>:<action>` strings the user has on org_id.
    """
    granted: set[str] = set()
    for ur in user.roles:
        if ur.organization_id == org_id:
            for perm in ur.role.permissions:
                granted.add(perm.name)
    return granted


def _bucket(granted: set[str]) -> dict[str, list[str]]:
    """Convert a flat set of "resource:action" strings into a resource->actions map.

    The contract is `<resource>:<action>`. Phase 2 will validate this at
    the database boundary; for Phase 1 the resolver trusts the upstream
    Pydantic model (`Permission.name` is the source of truth).
    """
    out: dict[str, list[str]] = {}
    for token in granted:
        resource, _, action = token.partition(":")
        # Pydantic enforces `name` as a non-empty string with `min_length=1`,
        # and the contract requires the `<resource>:<action>` shape. Defensive
        # shape checks are unnecessary here and would mask data integrity
        # issues; the resolver trusts the upstream model.
        out.setdefault(resource, []).append(action)
    # Stable ordering for tests.
    for resource in out:
        out[resource] = sorted(set(out[resource]))
    return out


@tracer.start_as_current_span("auth.permissions_service.resolve_permissions")
def resolve_permissions(
    user: UserProfile,
    current_organization_id: Optional[UUID],
) -> MyPermissions:
    """Resolve the user's effective permissions on the current org.

    Resolution order (Phase 1 stub):
      1. platform_admin role (anywhere) -> wildcard {"*": ["*"]}.
      2. org_admin role on the current org -> every org-scoped action
         from that role's permission list.
      3. any other role on the current org -> the actions attached to
         that role for the current org, bucketed by resource.
      4. no role on the current org -> empty permissions.

    Args:
        user: The authenticated user's profile (with roles loaded).
        current_organization_id: The org context, or None for no-org /
            platform-only contexts.

    Returns:
        MyPermissions: A permissions object scoped to the current org.
        Returns an empty object (no permissions) when the user has no role
        on the current org.
    """
    current_span = trace.get_current_span()
    if user.id is not None:
        current_span.set_attribute("user.id", str(user.id))
    if current_organization_id is not None:
        current_span.set_attribute(
            "org.id", str(current_organization_id)
        )

    # 1) Platform admin wildcard.
    if _is_platform_admin(user):
        current_span.set_attribute("permissions.source", "platform_admin_wildcard")
        return MyPermissions(
            current_organization_id=current_organization_id,
            permissions={WILDCARD_RESOURCE: [WILDCARD_ACTION]},
        )

    # No org context -> nothing to grant org-scoped permissions against.
    if current_organization_id is None:
        current_span.set_attribute("permissions.source", "no_org")
        return MyPermissions(
            current_organization_id=None,
            permissions={},
        )

    # 2 + 3) The user has some role on the current org: collect the actions.
    if _is_member_of(user, current_organization_id):
        granted = _actions_from_role(user, current_organization_id)
        permissions = _bucket(granted)
        current_span.set_attribute("permissions.source", "role_lookup")
        current_span.set_attribute("permissions.count", len(granted))
        return MyPermissions(
            current_organization_id=current_organization_id,
            permissions=permissions,
        )

    # 4) Not a member of the current org.
    current_span.set_attribute("permissions.source", "not_a_member")
    return MyPermissions(
        current_organization_id=current_organization_id,
        permissions={},
    )


# Re-export for tests and callers that want a class-style import.
class MyPermissionsService:
    """Thin class wrapper around `resolve_permissions`.

    Kept for symmetry with other services (`RBACService`, `BillingService`,
    `PermissionService`). The resolver itself is a pure function; this
    class is for future stateful extensions (e.g. caching, telemetry).
    """

    def resolve(
        self,
        user: UserProfile,
        current_organization_id: Optional[UUID],
    ) -> MyPermissions:
        """Resolve permissions for the given user on the given org context."""
        return resolve_permissions(user, current_organization_id)


my_permissions_service = MyPermissionsService()
