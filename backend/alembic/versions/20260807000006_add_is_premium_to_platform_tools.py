"""Add premium flag to platform_tools.

Revision ID: 20260807000006
Revises: 20260807000005
Create Date: 2026-08-07

Platform admins mark a tool ``is_premium`` to gate it behind the
``premium_tools`` plan-version feature entitlement. Org admins on plans
without that feature see the tool with a Premium badge and are blocked from
attaching it to agents.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260807000006"
down_revision: Union[str, None] = "20260807000005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "platform_tools",
        sa.Column("is_premium", sa.BOOLEAN(), server_default=sa.text("false"), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("platform_tools", "is_premium")
