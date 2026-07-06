"""
Tests for the N1 org_admin / regular_user RBAC extension migration.

The migration is a one-shot data fix: it inserts the new permission
rows that the N1 nav gate requires and wires them into the
``org_admin`` and ``regular_user`` roles. This test pins the
contract so a future change to either the migration or the
upstream permission list is caught early.

We test the migration as a pure module:
    1. Every name the migration promises to grant to ``org_admin``
       is present in NEW_PERMISSIONS.
    2. Every name the migration promises to grant to ``regular_user``
       is a read action (and not ``platform:admin``).
    3. The migration's permission set covers every resource the
       N1 nav-config gates on.
    4. Every permission name is unique (defensive against typos).
    5. Every (resource, action) pair is unique (the seed DB has a
       uniqueness expectation on name, and we want a 1:1 mapping
       between the pair and the name).
    6. The SQL builders escape single quotes correctly (defensive
       against a future description with an apostrophe).
"""

import importlib.util
import os
import re
import sys
from pathlib import Path

# --- Load the migration module directly so we can inspect its
# constants without bootstrapping the alembic env. -------------------

MIGRATION_PATH = Path(__file__).resolve().parents[2] / (
    "alembic/versions/" "20260705000001_extend_org_admin_and_regular_user_grants.py"
)


def _load_migration_module():
    """Import the migration file as a module so we can inspect its
    constants and helpers.

    We can't ``import`` it normally because it does ``from alembic
    import op`` at module top, and the test environment may not have
    alembic on the path. We work around that by stubbing ``alembic.op``
    with a no-op before executing the module.
    """
    spec = importlib.util.spec_from_file_location("n1_grants_migration", MIGRATION_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"could not load {MIGRATION_PATH}")

    # Stub the alembic package if it isn't installed in this env.
    import types

    if "alembic" not in sys.modules:
        fake_alembic = types.ModuleType("alembic")
        fake_alembic.op = types.SimpleNamespace(execute=lambda *a, **kw: None)
        sys.modules["alembic"] = fake_alembic

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# --- Tests ----------------------------------------------------------


def test_migration_file_exists():
    """The migration file is where we expect it to be."""
    assert (
        MIGRATION_PATH.exists()
    ), f"Expected migration at {MIGRATION_PATH} but it does not exist."


def test_new_permissions_is_non_empty():
    m = _load_migration_module()
    assert m.NEW_PERMISSIONS, "NEW_PERMISSIONS must be a non-empty tuple"


def test_every_permission_name_is_unique():
    m = _load_migration_module()
    names = [name for (_r, _a, name, _d) in m.NEW_PERMISSIONS]
    duplicates = [n for n in names if names.count(n) > 1]
    assert not duplicates, f"Duplicate permission names: {duplicates}"


def test_every_resource_action_pair_is_unique():
    """Defensive: a permission is identified by (resource, action),
    so duplicates here would also be duplicate names."""
    m = _load_migration_module()
    pairs = [(r, a) for (r, a, _n, _d) in m.NEW_PERMISSIONS]
    seen = set()
    for pair in pairs:
        assert pair not in seen, f"Duplicate (resource, action): {pair}"
        seen.add(pair)


def test_every_name_is_resource_colon_action():
    """Permission names follow the contract ``<resource>:<action>``."""
    m = _load_migration_module()
    pattern = re.compile(r"^[a-z_]+:[a-z_]+$")
    for _r, _a, name, _d in m.NEW_PERMISSIONS:
        assert pattern.match(name), f"Malformed permission name: {name!r}"


def test_org_admin_gets_every_new_permission_except_platform_admin():
    """org_admin receives every NEW_PERMISSIONS name EXCEPT
    ``platform:admin``.

    The migration's org_admin grant is built from NEW_PERMISSIONS
    with a single filter: drop the ``platform:admin`` row (which is
    reserved for the ``platform_admin`` role via the Phase 1
    ``*:*`` wildcard). The exclusion is explicit because the
    platform-level pages are role-gated on the backend.

    The assertion is over the source-of-truth lists
    (NEW_PERMISSIONS and ORG_ADMIN_GRANT_NAMES), not a hardcoded
    copy of either.
    """
    m = _load_migration_module()
    new_perm_names = {name for (_r, _a, name, _d) in m.NEW_PERMISSIONS}
    expected_grants = new_perm_names - {"platform:admin"}
    assert set(m.ORG_ADMIN_GRANT_NAMES) == expected_grants


def test_regular_user_only_gets_read_actions_and_no_platform_admin():
    """regular_user only receives read actions, and never
    ``platform:admin``. The filter is::

        action == "read" and resource != "platform"

    which (combined with the fact that ``billing:manage`` is the only
    billing permission in NEW_PERMISSIONS, and it has action ==
    "manage", not "read") means regular_user gets zero
    ``billing:*`` grants from this migration's NEW_PERMISSIONS list.

    The defensive DELETE in step 4 of ``upgrade()`` covers any
    pre-existing ``billing:*`` grant (e.g. a future seed that adds
    ``billing:read`` for regular_user); that is locked in by
    ``test_regular_user_migration_strips_any_billing_grant`` below.
    """
    m = _load_migration_module()
    derived = {
        name
        for (resource, action, name, _d) in m.NEW_PERMISSIONS
        if action == "read" and resource != "platform"
    }
    # No write / manage / admin actions.
    for name in derived:
        assert name.endswith(":read"), f"non-read permission leaked: {name}"
    # And no platform:admin leaks.
    assert "platform:admin" not in derived
    # And no billing permission of any action.
    billing_in_derived = {n for n in derived if n.startswith("billing:")}
    assert (
        not billing_in_derived
    ), f"regular_user grant list contains billing perms: {billing_in_derived}"


def test_migration_covers_every_resource_the_n1_nav_gates_on():
    """The N1 nav-config gates on a fixed set of resources. The
    migration must define at least the read permission for each so
    that the new contract is testable for an org_admin user.

    Resources the nav-config exposes (per
    ``docs/tw-drafts/navigation-redesign.md`` Section 6.5 and the
    ``NAV_SECTIONS`` constant in
    ``frontend/src/components/layout/nav-config.ts``):

        agent, phone_number, skill, call_log, member, billing, platform
    """
    m = _load_migration_module()
    resources_in_migration = {r for (r, _a, _n, _d) in m.NEW_PERMISSIONS}
    expected = {
        "agent",
        "phone_number",
        "skill",
        "call_log",
        "member",
        "billing",
        "platform",
    }
    missing = expected - resources_in_migration
    assert not missing, f"Migration is missing resources the N1 nav exposes: {missing}"


def test_org_admin_receives_billing_manage_but_not_platform_admin():
    """Two specific gates the N1 nav uses that are NOT covered by
    the initial RBAC seed:

        billing:manage  -> the "Billing" nav item
        platform:admin  -> the "All Users" and "Platform Skills" nav items

    The org_admin grant should include ``billing:manage`` (so an org
    admin can manage billing for their own org) but MUST NOT include
    ``platform:admin``: the platform-level pages (``/users`` and
    ``/platform/skills``) are gated by ``user.hasRole("platform_admin")``
    on the backend, and the nav section for platform_admin is now
    role-gated (see Option C in the N1 design doc). Granting
    ``platform:admin`` to ``org_admin`` would let the nav promise
    what the page denies.

    The ``platform:admin`` row itself stays in ``NEW_PERMISSIONS`` so
    the permission exists for any future role that should hold it
    (e.g. a new custom role), but no role other than ``platform_admin``
    receives it from this migration.
    """
    m = _load_migration_module()
    names = {name for (_r, _a, name, _d) in m.NEW_PERMISSIONS}
    assert "billing:manage" in names
    assert "platform:admin" in names  # row exists in NEW_PERMISSIONS
    # The org_admin grant must NOT include platform:admin.
    assert m.ORG_ADMIN_GRANT_NAMES is not None, (
        "Migration should expose ORG_ADMIN_GRANT_NAMES so the grant set "
        "is testable as a constant, not just inferred from SQL."
    )
    assert "platform:admin" not in m.ORG_ADMIN_GRANT_NAMES, (
        "org_admin must not receive platform:admin — the platform "
        "section is now role-gated and the pages do a hard role check."
    )
    # But billing:manage must still be there.
    assert "billing:manage" in m.ORG_ADMIN_GRANT_NAMES


def test_regular_user_migration_strips_any_billing_grant():
    """Product rule: regular_user must have ZERO ``billing:*`` grants
    after this migration runs.

    Step 3 of ``upgrade()`` already filters the NEW_PERMISSIONS list
    so that no billing permission is added to regular_user, but
    that's not enough on its own — if the Phase 1 seed (or any
    later data fix) ever grants ``billing:read`` (or any other
    billing action) to ``regular_user``, the N1 nav would
    incorrectly show the Billing item to regular members.

    Step 4 of ``upgrade()`` is a defensive DELETE that strips any
    ``billing:*`` grant from ``regular_user``. This test reads the
    migration's source as text and asserts that the DELETE is
    present, scoped to ``regular_user`` and ``resource = 'billing'``.
    """
    src = MIGRATION_PATH.read_text()
    # The DELETE must exist.
    assert "DELETE FROM role_permissions" in src, (
        "Migration is missing the defensive DELETE FROM role_permissions "
        "that strips billing grants from regular_user."
    )
    # The DELETE must target regular_user, not org_admin or platform_admin.
    delete_block = src[
        src.index("DELETE FROM role_permissions") : src.index(
            "DELETE FROM role_permissions"
        )
        + 600
    ]
    assert "regular_user" in delete_block, "Defensive DELETE must target regular_user."
    assert (
        "resource = 'billing'" in delete_block
    ), "Defensive DELETE must target the billing resource."
    # The DELETE must NOT touch org_admin or platform_admin.
    assert (
        "org_admin" not in delete_block
    ), "Defensive DELETE must not strip org_admin's billing grants."
    assert (
        "platform_admin" not in delete_block
    ), "Defensive DELETE must not strip platform_admin's billing grants."


def test_format_perm_values_sql_escapes_single_quotes():
    """Defensive: descriptions with apostrophes must not break the
    generated SQL.
    """
    m = _load_migration_module()
    sql = m._format_perm_values_sql(
        (("agent", "read", "agent:read", "It's a permission"),)
    )
    # The apostrophe in "It's" must be doubled to ''.
    assert "'It''s a permission'" in sql
    # And the whole row must still parse as a single VALUES tuple.
    assert sql.count("(") == 1 and sql.count(")") == 1
    # All four columns are emitted in the order
    # (name, description, resource, action) so the generated SQL
    # matches the explicit column list in the migration's INSERT.
    assert "'agent:read'" in sql  # name
    assert "'agent'" in sql  # resource
    assert "'read'" in sql  # action


def test_format_perm_values_sql_emits_resource_and_action():
    """The ``permissions`` table has NOT NULL columns ``resource``
    and ``action``. The VALUES tuple emitted by the helper must
    include them, otherwise the INSERT fails with
    ``null value in column "resource" of relation "permissions"
    violates not-null constraint``.

    This test pins the (name, description, resource, action) column
    order against a regression where someone narrows the helper
    back to (name, description).
    """
    m = _load_migration_module()
    sql = m._format_perm_values_sql(
        (("phone_number", "read", "phone_number:read", "Read PNs"),)
    )
    # 4 quoted columns inside the single VALUES tuple.
    assert sql == "('phone_number:read', 'Read PNs', 'phone_number', 'read')"


def test_format_name_array_sql_escapes_single_quotes():
    m = _load_migration_module()
    arr = m._format_name_array_sql(["agent:read", "weird'name"])
    assert "'agent:read'" in arr
    assert "'weird''name'" in arr
    # Wraps in ARRAY[ ... ].
    assert arr.startswith("ARRAY[") and arr.endswith("]")


def test_revision_and_down_revision_match_project_conventions():
    """Sanity-check the alembic metadata so a typo in the revision
    or down_revision is caught before the migration is ever run.
    """
    m = _load_migration_module()
    assert m.revision == "20260705000001"
    assert m.down_revision == "20260624000001"
    assert m.branch_labels in (None, (), [])
    assert m.depends_on in (None, (), [])
