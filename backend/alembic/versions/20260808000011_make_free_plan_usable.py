"""Make the published free plan usable after subscription-aware onboarding.

The original free fallback deliberately had ``max_agents = 0`` while the old
onboarding wizard attempted to create an agent. The new onboarding flow no
longer creates an agent, so the explicit free plan can safely allow one agent
and provide a small recurring credit allowance for exploration.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "20260808000011"
down_revision: Union[str, None] = "20260808000010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Update the current free version's deliberate starter entitlements."""
    op.execute(
        """
        UPDATE plan_version_entitlements pve
        SET value = '{"type": "integer", "value": 1}'::jsonb
        FROM plan_versions pv
        JOIN plan_products pp ON pp.id = pv.plan_product_id
        WHERE pve.plan_version_id = pv.id
          AND pp.slug = 'free'
          AND pv.is_current_for_signup = true
          AND pve.entitlement_key = 'max_agents'
        """
    )
    op.execute(
        """
        INSERT INTO plan_version_entitlements (plan_version_id, entitlement_key, value)
        SELECT pv.id, 'included_credits_per_billing_period',
               '{"type": "integer", "value": 100}'::jsonb
        FROM plan_versions pv
        JOIN plan_products pp ON pp.id = pv.plan_product_id
        WHERE pp.slug = 'free'
          AND pv.is_current_for_signup = true
        ON CONFLICT (plan_version_id, entitlement_key) DO UPDATE
        SET value = EXCLUDED.value
        """
    )


def downgrade() -> None:
    """Restore the previous zero-agent free fallback."""
    op.execute(
        """
        UPDATE plan_version_entitlements pve
        SET value = '{"type": "integer", "value": 0}'::jsonb
        FROM plan_versions pv
        JOIN plan_products pp ON pp.id = pv.plan_product_id
        WHERE pve.plan_version_id = pv.id
          AND pp.slug = 'free'
          AND pv.is_current_for_signup = true
          AND pve.entitlement_key = 'max_agents'
        """
    )
    op.execute(
        """
        DELETE FROM plan_version_entitlements pve
        USING plan_versions pv, plan_products pp
        WHERE pve.plan_version_id = pv.id
          AND pv.plan_product_id = pp.id
          AND pp.slug = 'free'
          AND pv.is_current_for_signup = true
          AND pve.entitlement_key = 'included_credits_per_billing_period'
        """
    )
