"""Add an optional public result destination for demo receipts.

The URL is configured by platform administrators for a dedicated public demo
view such as a Google Sheet. It is returned only on successful, signed demo
outcome receipts; it is not exposed on the public demo landing page.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260901000001"
down_revision: Union[str, None] = "20260830000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add the nullable platform-admin-configured receipt destination."""
    op.add_column(
        "voice_agents",
        sa.Column("demo_public_result_url", sa.String(length=2048), nullable=True),
    )


def downgrade() -> None:
    """Remove the demo receipt destination setting."""
    op.drop_column("voice_agents", "demo_public_result_url")
