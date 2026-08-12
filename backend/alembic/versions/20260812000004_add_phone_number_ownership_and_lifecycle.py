"""Add ownership, webhook verification, and provisioning lifecycle state."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260812000004"
down_revision: Union[str, None] = "20260812000003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Make platform and customer-managed Twilio numbers explicit and routable."""
    op.add_column(
        "phone_numbers",
        sa.Column(
            "provisioning_source",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'platform'"),
        ),
    )
    op.add_column(
        "phone_numbers",
        sa.Column(
            "management_mode",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'platform_managed'"),
        ),
    )
    op.add_column(
        "phone_numbers",
        sa.Column(
            "configuration_status",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'configured'"),
        ),
    )
    op.add_column(
        "phone_numbers",
        sa.Column(
            "billing_mode",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'platform_rental'"),
        ),
    )
    op.add_column(
        "phone_numbers",
        sa.Column("connection_token_hash", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "phone_numbers",
        sa.Column("provisioning_idempotency_key", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "phone_numbers",
        sa.Column("configuration_error", sa.String(length=1000), nullable=True),
    )
    op.add_column(
        "phone_numbers",
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_check_constraint(
        "ck_phone_numbers_status",
        "phone_numbers",
        "status IN ('available', 'provisioning', 'purchased', 'active', 'inactive', "
        "'cancelled', 'verification_required', 'release_pending', 'disconnected')",
    )
    op.create_check_constraint(
        "ck_phone_numbers_management_mode",
        "phone_numbers",
        "management_mode IN ('platform_managed', 'customer_managed')",
    )
    op.create_check_constraint(
        "ck_phone_numbers_billing_mode",
        "phone_numbers",
        "billing_mode IN ('platform_rental', 'none')",
    )
    op.create_check_constraint(
        "ck_phone_numbers_configuration_status",
        "phone_numbers",
        "configuration_status IN ('pending', 'configured', 'verification_required', 'failed')",
    )
    op.create_index(
        "uq_phone_numbers_active_number",
        "phone_numbers",
        ["phone_number"],
        unique=True,
        postgresql_where=sa.text("status NOT IN ('cancelled', 'disconnected')"),
    )
    op.create_index(
        "uq_phone_numbers_connection_token_hash",
        "phone_numbers",
        ["connection_token_hash"],
        unique=True,
        postgresql_where=sa.text("connection_token_hash IS NOT NULL"),
    )
    op.create_index(
        "uq_phone_numbers_provisioning_idempotency",
        "phone_numbers",
        ["organization_id", "provisioning_idempotency_key"],
        unique=True,
        postgresql_where=sa.text("provisioning_idempotency_key IS NOT NULL"),
    )
    op.create_index(
        "ix_phone_numbers_release_pending",
        "phone_numbers",
        ["status", "updated_at"],
        postgresql_where=sa.text("status = 'release_pending'"),
    )


def downgrade() -> None:
    """Remove ownership and lifecycle fields."""
    op.drop_index("ix_phone_numbers_release_pending", table_name="phone_numbers")
    op.drop_index("uq_phone_numbers_connection_token_hash", table_name="phone_numbers")
    op.drop_index(
        "uq_phone_numbers_provisioning_idempotency", table_name="phone_numbers"
    )
    op.drop_index("uq_phone_numbers_active_number", table_name="phone_numbers")
    op.drop_constraint(
        "ck_phone_numbers_configuration_status", "phone_numbers", type_="check"
    )
    op.drop_constraint("ck_phone_numbers_billing_mode", "phone_numbers", type_="check")
    op.drop_constraint(
        "ck_phone_numbers_management_mode", "phone_numbers", type_="check"
    )
    op.drop_constraint("ck_phone_numbers_status", "phone_numbers", type_="check")
    op.drop_column("phone_numbers", "last_verified_at")
    op.drop_column("phone_numbers", "configuration_error")
    op.drop_column("phone_numbers", "connection_token_hash")
    op.drop_column("phone_numbers", "provisioning_idempotency_key")
    op.drop_column("phone_numbers", "billing_mode")
    op.drop_column("phone_numbers", "configuration_status")
    op.drop_column("phone_numbers", "management_mode")
    op.drop_column("phone_numbers", "provisioning_source")
