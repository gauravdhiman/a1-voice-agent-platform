"""Add explicit metering dimensions to platform credit events."""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "20260811000001"
down_revision: Union[str, None] = "20260810000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add meter/unit fields and seed call-recording storage pricing."""
    op.add_column(
        "credit_events",
        sa.Column(
            "meter_type",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'count'"),
        ),
    )
    op.add_column(
        "credit_events",
        sa.Column(
            "billing_unit",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'event'"),
        ),
    )
    op.create_check_constraint(
        "ck_credit_events_meter_type",
        "credit_events",
        "meter_type IN ('count', 'duration', 'storage')",
    )
    op.create_check_constraint(
        "ck_credit_events_billing_unit",
        "credit_events",
        "billing_unit IN ('event', 'minute', 'day', 'month')",
    )
    op.create_check_constraint(
        "ck_credit_events_meter_unit_compatibility",
        "credit_events",
        "(meter_type = 'count' AND billing_unit = 'event') OR "
        "(meter_type = 'duration' AND billing_unit = 'minute') OR "
        "(meter_type = 'storage' AND billing_unit IN ('day', 'month'))",
    )

    op.execute(
        """
        UPDATE credit_events
        SET meter_type = 'duration', billing_unit = 'minute'
        WHERE name = 'voice_call_minute'
        """
    )
    op.execute(
        """
        INSERT INTO credit_events (
            name, description, credit_cost, category, is_active,
            meter_type, billing_unit
        )
        VALUES (
            'call_recording_storage',
            'Call recording storage retained for one billing month',
            0,
            'storage',
            TRUE,
            'storage',
            'month'
        )
        ON CONFLICT (name) DO NOTHING
        """
    )


def downgrade() -> None:
    """Remove explicit credit-event metering dimensions and seed row."""
    op.execute("DELETE FROM credit_events WHERE name = 'call_recording_storage'")
    op.drop_constraint(
        "ck_credit_events_meter_unit_compatibility", "credit_events", type_="check"
    )
    op.drop_constraint("ck_credit_events_billing_unit", "credit_events", type_="check")
    op.drop_constraint("ck_credit_events_meter_type", "credit_events", type_="check")
    op.drop_column("credit_events", "billing_unit")
    op.drop_column("credit_events", "meter_type")
