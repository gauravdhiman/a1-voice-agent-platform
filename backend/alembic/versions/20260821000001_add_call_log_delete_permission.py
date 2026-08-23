"""add call_log:delete permission and grant it to org_admin

Revision ID: 20260821000001
Revises: 20260819000001
Create Date: 2026-08-21

Adds the ``call_log:delete`` permission so organization administrators can
delete call recordings (audio objects) while keeping call-log rows intact
for audit. regular_user is intentionally NOT granted this permission —
recording deletion is an admin-only action (see permission-matrix.md).

The pattern mirrors 20260705000001_extend_org_admin_and_regular_user_grants:
idempotent inserts on ``permissions.name`` and on the ``role_permissions``
PK so re-runs are safe.

Downstream consumers:
    - backend/src/call_artifacts/routes.py (_check_delete_access)
    - frontend/src/lib/permissions.ts (P.callLog.delete)
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260821000001"
down_revision: Union[str, None] = "20260819000001"
branch_labels: Union[str, Sequence[str]] = None
depends_on: Union[str, Sequence[str]] = None

PERMISSION_NAME = "call_log:delete"
DESCRIPTION = (
    "Delete call recordings (audio only; call log rows are kept for audit)"
)


def upgrade() -> None:
    # 1. Insert the permission row (idempotent on `name`).
    name_lit = PERMISSION_NAME.replace("'", "''")
    desc_lit = DESCRIPTION.replace("'", "''")
    resource_lit = "call_log"
    action_lit = "delete"
    op.execute(
        f"""
        INSERT INTO permissions (name, description, resource, action) VALUES
            ('{name_lit}', '{desc_lit}', '{resource_lit}', '{action_lit}')
        ON CONFLICT (name) DO NOTHING
    """
    )

    # 2. Grant it to org_admin only (idempotent via NOT EXISTS).
    op.execute(
        f"""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r
        CROSS JOIN permissions p
        WHERE r.name = 'org_admin'
          AND p.name = '{name_lit}'
          AND NOT EXISTS (
              SELECT 1 FROM role_permissions rp
              WHERE rp.role_id = r.id AND rp.permission_id = p.id
          )
    """
    )


def downgrade() -> None:
    # Remove the org_admin grant first, then the permission row itself,
    # so no dangling role_permissions references remain.
    op.execute(
        f"""
        DELETE FROM role_permissions
        WHERE permission_id IN (
            SELECT id FROM permissions WHERE name = '{PERMISSION_NAME}'
        )
    """
    )
    op.execute(
        f"DELETE FROM permissions WHERE name = '{PERMISSION_NAME}'"
    )