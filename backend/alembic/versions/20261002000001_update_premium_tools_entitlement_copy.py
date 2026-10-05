"""Update premium tool entitlement display metadata.

Revision ID: 20261002000001
Revises: 20261001000006
Create Date: 2026-10-02
"""

from typing import Sequence, Union

from alembic import op

revision: str = "20261002000001"
down_revision: Union[str, Sequence[str], None] = "20261001000006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Name the premium_tools entitlement and list included integrations."""
    op.execute(
        """
        UPDATE entitlement_definitions
         SET display_name = 'Premium integrations',
               description = 'Includes Gmail, Google Sheets, HubSpot lead capture, and Cal.com scheduling.'
         WHERE key = 'premium_tools'
           AND display_name = 'Premium tools'
           AND description = 'Access to premium platform tools'
        """
    )


def downgrade() -> None:
    """Restore the previous generic entitlement copy when it is unchanged."""
    op.execute(
        """
        UPDATE entitlement_definitions
           SET display_name = 'Premium tools',
               description = 'Access to premium platform tools'
         WHERE key = 'premium_tools'
           AND display_name = 'Premium integrations'
           AND description = 'Includes Gmail, Google Sheets, HubSpot lead capture, and Cal.com scheduling.'
        """
    )
