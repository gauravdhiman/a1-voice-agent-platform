"""Enable row-level security on the billing notification outbox."""

from typing import Sequence, Union

from alembic import op

revision: str = "20260812000001"
down_revision: Union[str, None] = "20260811000005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Protect outbox rows from direct client access."""
    op.execute("ALTER TABLE credit_notification_outbox ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    """Disable row-level security when reverting this additive hardening."""
    op.execute("ALTER TABLE credit_notification_outbox DISABLE ROW LEVEL SECURITY")
