"""Store safe runtime failure details on voice call logs.

The fields are intentionally short, stable classifications rather than raw
provider exceptions. Raw diagnostics remain in the service logs/telemetry
boundary and are not exposed through the call-log API.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260902000001"
down_revision: Union[str, None] = "20260901000002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add nullable failure classification fields to call logs."""
    op.add_column(
        "call_logs",
        sa.Column("failure_code", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "call_logs",
        sa.Column("failure_message", sa.String(length=1000), nullable=True),
    )
    op.create_index("ix_call_logs_failure_code", "call_logs", ["failure_code"])


def downgrade() -> None:
    """Remove the runtime failure classification fields."""
    op.drop_index("ix_call_logs_failure_code", table_name="call_logs")
    op.drop_column("call_logs", "failure_message")
    op.drop_column("call_logs", "failure_code")
