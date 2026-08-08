"""Allow free plan subscriptions without Stripe customer identifiers."""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "20260807000009"
down_revision: Union[str, None] = "20260807000008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Make Stripe customer identity optional for explicitly free plans."""
    op.alter_column(
        "organization_subscriptions",
        "stripe_customer_id",
        existing_type=sa.VARCHAR(length=255),
        nullable=True,
    )


def downgrade() -> None:
    """Restore the legacy required Stripe customer identity constraint."""
    op.alter_column(
        "organization_subscriptions",
        "stripe_customer_id",
        existing_type=sa.VARCHAR(length=255),
        nullable=False,
    )
