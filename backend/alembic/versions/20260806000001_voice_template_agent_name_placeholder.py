"""Replace hard-coded template agent names with [Agent Name] placeholder.

Revision ID: 20260806000001
Revises: 20260804000001
Create Date: 2026-08-06

Updates seeded voice_templates greetings/personas so onboarding can substitute
the user-chosen agent name instead of Alex/Jordan/Taylor/Morgan/Casey.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "20260806000001"
down_revision: Union[str, None] = "20260804000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Rewrite seed template copy to use [Agent Name] placeholders."""
    op.execute(
        """
        UPDATE voice_templates
        SET
          persona = REPLACE(
            REPLACE(
              REPLACE(
                REPLACE(
                  REPLACE(persona, 'named Alex', 'named [Agent Name]'),
                  'named Jordan', 'named [Agent Name]'
                ),
                'named Taylor', 'named [Agent Name]'
              ),
              'named Morgan', 'named [Agent Name]'
            ),
            'named Casey', 'named [Agent Name]'
          ),
          greeting = REPLACE(
            REPLACE(
              REPLACE(
                REPLACE(
                  REPLACE(greeting, 'This is Alex', 'This is [Agent Name]'),
                  'This is Jordan', 'This is [Agent Name]'
                ),
                'This is Taylor', 'This is [Agent Name]'
              ),
              'This is Morgan', 'This is [Agent Name]'
            ),
            'This is Casey', 'This is [Agent Name]'
          )
        WHERE greeting IS NOT NULL OR persona IS NOT NULL
        """
    )


def downgrade() -> None:
    """No-op: hard-coded names are not restored (data was genericized)."""
    pass
