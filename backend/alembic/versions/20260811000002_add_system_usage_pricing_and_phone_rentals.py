"""Add fixed system usage prices and monthly phone-rental state."""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "20260811000002"
down_revision: Union[str, None] = "20260811000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Seed canonical prices and add phone-number renewal/grace fields."""
    op.drop_constraint(
        "ck_credit_events_meter_unit_compatibility",
        "credit_events",
        type_="check",
    )
    op.create_check_constraint(
        "ck_credit_events_meter_unit_compatibility",
        "credit_events",
        "(meter_type = 'count' AND billing_unit IN ('event', 'month')) OR "
        "(meter_type = 'duration' AND billing_unit = 'minute') OR "
        "(meter_type = 'storage' AND billing_unit IN ('day', 'month'))",
    )

    op.execute(
        """
        UPDATE credit_events
        SET is_active = FALSE
        WHERE name IN (
            'api_call_basic', 'api_call_premium', 'storage_gb_month',
            'compute_hour', 'ai_inference', 'data_export',
            'webhook_delivery', 'phone_number_purchase',
            'call_recording_storage'
        )
        """
    )
    op.execute(
        """
        UPDATE credit_events
        SET description = 'A connected voice call is charged for each whole minute, rounded up.',
            category = 'voice',
            meter_type = 'duration',
            billing_unit = 'minute',
            is_active = TRUE
        WHERE name = 'voice_call_minute'
        """
    )
    op.execute(
        """
        INSERT INTO credit_events (
            name, description, credit_cost, category, is_active,
            meter_type, billing_unit
        ) VALUES
            (
                'phone_number_local_month',
                'An active local phone number is charged once for each rental month.',
                200, 'phone_number', TRUE, 'count', 'month'
            ),
            (
                'phone_number_mobile_month',
                'An active mobile phone number is charged once for each rental month.',
                200, 'phone_number', TRUE, 'count', 'month'
            ),
            (
                'phone_number_toll_free_month',
                'An active toll-free phone number is charged once for each rental month.',
                500, 'phone_number', TRUE, 'count', 'month'
            )
        ON CONFLICT (name) DO UPDATE SET
            description = EXCLUDED.description,
            category = EXCLUDED.category,
            meter_type = EXCLUDED.meter_type,
            billing_unit = EXCLUDED.billing_unit,
            is_active = TRUE
        """
    )

    op.add_column(
        "phone_numbers",
        sa.Column(
            "billing_status",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'active'"),
        ),
    )
    op.add_column(
        "phone_numbers",
        sa.Column("next_billing_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "phone_numbers",
        sa.Column("billing_grace_ends_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_check_constraint(
        "ck_phone_numbers_billing_status",
        "phone_numbers",
        "billing_status IN ('active', 'past_due')",
    )
    op.create_index(
        "ix_phone_numbers_next_billing_at",
        "phone_numbers",
        ["next_billing_at"],
    )


def downgrade() -> None:
    """Remove phone rental fields and restore the previous meter constraint."""
    op.drop_index("ix_phone_numbers_next_billing_at", table_name="phone_numbers")
    op.drop_constraint(
        "ck_phone_numbers_billing_status", "phone_numbers", type_="check"
    )
    op.drop_column("phone_numbers", "billing_grace_ends_at")
    op.drop_column("phone_numbers", "next_billing_at")
    op.drop_column("phone_numbers", "billing_status")
    op.execute(
        "DELETE FROM credit_events WHERE name IN "
        "('phone_number_local_month', 'phone_number_mobile_month', "
        "'phone_number_toll_free_month')"
    )
    op.drop_constraint(
        "ck_credit_events_meter_unit_compatibility",
        "credit_events",
        type_="check",
    )
    op.create_check_constraint(
        "ck_credit_events_meter_unit_compatibility",
        "credit_events",
        "(meter_type = 'count' AND billing_unit = 'event') OR "
        "(meter_type = 'duration' AND billing_unit = 'minute') OR "
        "(meter_type = 'storage' AND billing_unit IN ('day', 'month'))",
    )
