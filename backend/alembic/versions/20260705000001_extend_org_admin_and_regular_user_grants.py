"""extend org_admin and regular_user grants to cover the N1 nav resources

Revision ID: 20260705000001
Revises: 20260624000001
Create Date: 2026-07-05 00:00:01.000000

The Phase 1 RBAC seed in 91759229c32b only knew about user/
organization/role/permission/billing/platform resources. The N1 nav
redesign exposes:

    workspace:    agent, phone_number, skill, call_log
    org_admin:    member, billing:manage
    platform:     platform:admin

The permissions_service resolver on /me just buckets the
role-permissions by ``<resource>:<action>``, so the only thing
missing for org_admins and regular_users to see those nav items is
the actual permission rows + role_permissions grants.

Product rules encoded here (N1 follow-up; see also
``docs/tw-drafts/navigation-redesign.md``):

    * platform_admin -> full wildcard ({"*": ["*"]}). Already wired
      in permissions_service via the existing ``*:*`` seed; nothing
      to add for this role.
    * org_admin -> all CRUD on every org-scoped resource (agent,
      phone_number, skill, call_log, member, billing:manage,
      organization, user) PLUS the ``billing:manage`` composite
      permission. The ``platform:admin`` permission row is
      *introduced* by this migration but is NOT granted to
      ``org_admin``: the platform-level pages (``/users`` and
      ``/platform/skills``) are role-gated on the backend
      (``user.hasRole("platform_admin")``) and the nav section is
      now role-gated too (Option C in the N1 design doc).
      Granting ``platform:admin`` to ``org_admin`` would let the
      nav promise what the page denies. The row stays in
      ``NEW_PERMISSIONS`` so the permission exists for any future
      role that should hold it.
    * regular_user -> read on every org-scoped resource.
      Billing is OFF-LIMITS for regular members: no read, no
      write, no manage, no subscribe. The ``regular_user`` row in
      the role_permissions table is therefore explicitly cleared of
      any ``billing:*`` grant (defence in depth — the Phase 1 seed
      already does not grant any billing permission to
      ``regular_user``, but this migration locks the rule in so a
      future seed change cannot accidentally re-introduce it).
      The DOWN migration intentionally does NOT restore any
      ``billing:*`` grant that the upgrade stripped: the product
      rule (regular_user has no billing access) survives a
      downgrade, which is the correct, conservative behaviour.

The migration is idempotent: every INSERT uses ``ON CONFLICT DO
NOTHING`` on the unique ``permissions.name`` and a ``NOT EXISTS``
guard on ``role_permissions`` so re-runs on a partially-applied DB
are safe.

A DOWN migration removes the new grants and the new permission rows
that this migration introduced. Pre-existing rows from the initial
seed are left untouched.
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260705000001"
down_revision: Union[str, None] = "20260624000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# All permissions this migration introduces. Mirrors the resources the
# N1 nav exposes plus the higher-level "manage" / "admin" actions the
# nav gates on.
NEW_PERMISSIONS: tuple[tuple[str, str, str, str], ...] = (
    # (resource, action, name, description)
    # --- agents ---
    ("agent", "read", "agent:read", "View voice agents in the organization"),
    ("agent", "create", "agent:create", "Create voice agents in the organization"),
    ("agent", "update", "agent:update", "Update voice agents in the organization"),
    ("agent", "delete", "agent:delete", "Delete voice agents in the organization"),
    # --- phone numbers ---
    (
        "phone_number",
        "read",
        "phone_number:read",
        "View phone numbers in the organization",
    ),
    (
        "phone_number",
        "create",
        "phone_number:create",
        "Provision phone numbers in the organization",
    ),
    (
        "phone_number",
        "update",
        "phone_number:update",
        "Update phone number assignment/configuration",
    ),
    (
        "phone_number",
        "delete",
        "phone_number:delete",
        "Release phone numbers in the organization",
    ),
    # --- skills ---
    ("skill", "read", "skill:read", "View skills available to the organization"),
    ("skill", "create", "skill:create", "Create skills for the organization"),
    ("skill", "update", "skill:update", "Update skills for the organization"),
    ("skill", "delete", "skill:delete", "Delete skills for the organization"),
    # --- call logs ---
    ("call_log", "read", "call_log:read", "View call history and analytics"),
    # --- members (user-management) ---
    ("member", "read", "member:read", "View organization membership"),
    ("member", "create", "member:create", "Invite users to the organization"),
    (
        "member",
        "update",
        "member:update",
        "Update member roles within the organization",
    ),
    ("member", "delete", "member:delete", "Remove members from the organization"),
    # --- billing "manage" (composite gate the N1 nav uses) ---
    (
        "billing",
        "manage",
        "billing:manage",
        "Manage billing, subscriptions, and credit balance for the organization",
    ),
    # --- platform admin gate (composite permission the N1 nav uses) ---
    (
        "platform",
        "admin",
        "platform:admin",
        "Full control over platform-level resources",
    ),
)


# Derived constant: the set of NEW_PERMISSIONS that the org_admin
# role receives from this migration's step 2. Exposed at module
# scope so tests can assert the contract without parsing the
# generated SQL. The only filter is "drop platform:admin" because
# the platform-level pages (/users and /platform/skills) are
# role-gated on the backend (user.hasRole("platform_admin")) and
# the nav section is now role-gated too (Option C in the N1
# design doc). Granting platform:admin to org_admin would let the
# nav promise what the page denies.
ORG_ADMIN_GRANT_NAMES: tuple[str, ...] = tuple(
    name
    for (resource, _action, name, _d) in NEW_PERMISSIONS
    if not (resource == "platform" and _action == "admin")
)


# Derived constant: the set of NEW_PERMISSIONS that the regular_user
# role receives from this migration's step 3. Exposed at module
# scope for the same reason as ORG_ADMIN_GRANT_NAMES. The filter
# is "read action only" AND "not the platform resource" so the
# regular user is locked out of write/manage actions and any
# platform-level control.
REGULAR_USER_GRANT_NAMES: tuple[str, ...] = tuple(
    name
    for (resource, action, name, _d) in NEW_PERMISSIONS
    if action == "read" and resource != "platform"
)


def _format_perm_values_sql(perms: Sequence[tuple[str, str, str, str]]) -> str:
    """Render a multi-row VALUES clause for the permissions table.

    The ``permissions`` table has NOT NULL columns ``resource`` and
    ``action`` (see migration 91759229c32b_add_initial_rbac_tables
    for the schema), so the VALUES tuple has to include them too.
    The columns are emitted in the order::

        (name, description, resource, action)

    which matches the explicit column list in the INSERT.

    Single-quotes every textual field. Empty-string descriptions are
    not possible here because every entry in NEW_PERMISSIONS has a
    non-empty description, but the helper is defensive anyway.
    """
    rows = []
    for resource, action, name, description in perms:
        name_lit = name.replace("'", "''")
        desc_lit = description.replace("'", "''")
        resource_lit = resource.replace("'", "''")
        action_lit = action.replace("'", "''")
        rows.append(f"('{name_lit}', '{desc_lit}', '{resource_lit}', '{action_lit}')")
    return ",\n            ".join(rows)


def _format_name_array_sql(names: Sequence[str]) -> str:
    """Render a PostgreSQL text-array literal, e.g. ``'{a,b,c}'``.

    Used by the role_permissions grant / revoke queries so we don't
    depend on parameterised ``op.execute`` (the rest of the project's
    migrations inline SQL strings).
    """
    escaped = [n.replace("'", "''") for n in names]
    return "ARRAY[" + ",".join(f"'{e}'" for e in escaped) + "]"


def upgrade() -> None:
    # 1. Insert the new permission rows (idempotent on `name`).
    values_sql = _format_perm_values_sql(NEW_PERMISSIONS)
    op.execute(
        f"""
        INSERT INTO permissions (name, description, resource, action) VALUES
            {values_sql}
        ON CONFLICT (name) DO NOTHING
    """
    )

    # 2. Grant all the new permissions to org_admin except
    # ``platform:admin`` (idempotent via NOT EXISTS on the
    # role_permissions PK). The platform_admin role receives
    # ``*:*`` from the Phase 1 seed, so the platform-level pages
    # continue to work for that role.
    org_admin_array = _format_name_array_sql(ORG_ADMIN_GRANT_NAMES)
    op.execute(
        f"""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r
        CROSS JOIN permissions p
        WHERE r.name = 'org_admin'
          AND p.name = ANY ({org_admin_array})
          AND NOT EXISTS (
              SELECT 1 FROM role_permissions rp
              WHERE rp.role_id = r.id AND rp.permission_id = p.id
          )
    """
    )

    # 3. Grant only the read actions of the new permissions to
    # regular_user. ``platform:admin`` is excluded by the
    # resource filter; ``billing:manage`` is also excluded because
    # its action is "manage" not "read".
    regular_user_array = _format_name_array_sql(REGULAR_USER_GRANT_NAMES)
    op.execute(
        f"""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r
        CROSS JOIN permissions p
        WHERE r.name = 'regular_user'
          AND p.name = ANY ({regular_user_array})
          AND NOT EXISTS (
              SELECT 1 FROM role_permissions rp
              WHERE rp.role_id = r.id AND rp.permission_id = p.id
          )
    """
    )

    # 4. Enforce the product rule: regular_user must have ZERO
    # ``billing:*`` grants. The Phase 1 seed already keeps billing
    # off-limits for regular members, but this DELETE is defence in
    # depth — if a future seed or data fix ever grants
    # ``billing:read`` (or any other billing action) to
    # ``regular_user``, this migration will strip it so the contract
    # is preserved.
    #
    # The deletion is scoped to ``regular_user`` only and only
    # touches ``billing:*`` permissions, so it is safe to re-run
    # (idempotent). It also does not affect ``org_admin`` or
    # ``platform_admin``, both of which keep their billing grants.
    op.execute(
        """
        DELETE FROM role_permissions
        WHERE role_id = (SELECT id FROM roles WHERE name = 'regular_user')
          AND permission_id IN (
              SELECT id FROM permissions WHERE resource = 'billing'
          )
    """
    )


def downgrade() -> None:
    # Remove the grants this migration introduced, then remove the
    # permission rows this migration introduced. We do it in that order
    # so a partial downgrade doesn't leave dangling FK references.
    #
    # Note on the ``regular_user`` billing DELETE in the upgrade:
    # the DOWN does not restore any ``billing:*`` grant that the
    # upgrade stripped, because (a) the Phase 1 seed does not grant
    # any billing permission to ``regular_user`` and (b) there is no
    # portable way to record a per-process backup inside an alembic
    # migration without coupling to the migration runner. If a
    # future seed change adds a ``billing:read`` grant for
    # ``regular_user`` and this migration strips it, the DOWN will
    # leave it stripped. That is the correct, conservative behaviour:
    # the product rule (regular_user has no billing access) survives
    # a downgrade.
    new_perm_names = [name for (_r, _a, name, _d) in NEW_PERMISSIONS]
    name_array = _format_name_array_sql(new_perm_names)

    op.execute(
        f"""
        DELETE FROM role_permissions
        WHERE permission_id IN (
            SELECT id FROM permissions WHERE name = ANY ({name_array})
        )
    """
    )
    op.execute(f"DELETE FROM permissions WHERE name = ANY ({name_array})")
