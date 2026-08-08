"""Remove PAYG entitlements from the catalog and plan assignments.

Revision ID: 20260807000004
Revises: 20260807000003
Create Date: 2026-08-07

Business decision: the platform does not offer pay-as-you-go (postpaid)
usage. Credits are strictly prepaid — plan credits and purchased credit
packs. This migration removes ``payg_enabled`` and ``payg_credit_cap`` from
``entitlement_definitions`` (and any plan-version assignments), so runtime
resolution (which iterates active definitions) can no longer see them.

The downgrade restores the catalog definitions with their original values but
cannot restore plan-version assignments (they are deleted).
"""

from typing import Sequence, Union

from alembic import op

revision: str = "20260807000004"
down_revision: Union[str, None] = "20260807000003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PAYG_KEYS = ("payg_enabled", "payg_credit_cap")


def upgrade() -> None:
    op.execute(
        """
        DELETE FROM plan_version_entitlements
        WHERE entitlement_key IN ('payg_enabled', 'payg_credit_cap')
        """
    )
    op.execute(
        """
        DELETE FROM entitlement_definitions
        WHERE key IN ('payg_enabled', 'payg_credit_cap')
        """
    )


def downgrade() -> None:
    op.execute(
        """
        INSERT INTO entitlement_definitions
            (key, kind, display_name, value_type, unit, enforcement_handler,
             default_enforcement, default_when_absent, description,
             created_at, updated_at)
        VALUES
            ('payg_credit_cap', 'limit', 'PAYG credit cap', 'integer', 'credits',
             'limit.max_count', 'hard', NULL,
             'Maximum negative balance when PAYG enabled', NOW(), NOW()),
            ('payg_enabled', 'feature', 'Pay as you go', 'boolean', NULL,
             'feature.flag', 'hard', '{"type": "boolean", "value": false}'::jsonb,
             'Allow usage after included credits exhausted', NOW(), NOW())
        ON CONFLICT (key) DO NOTHING
        """
    )
