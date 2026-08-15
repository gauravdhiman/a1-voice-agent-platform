"""Canonicalize dynamic placeholders in seeded voice templates.

Revision ID: 20260814000002
Revises: 20260813000001
Create Date: 2026-08-14

The earlier voice-template migration used bracket markers such as
``[Agent Name]`` and ``[Business Name]``. Runtime prompt rendering supports
the canonical ``{{agent.name}}`` and ``{{org.name}}`` variables instead. This
forward-only data migration updates existing rows without changing any
customer-owned agent instructions.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "20260814000002"
down_revision: Union[str, None] = "20260813000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _canonicalize(column: str) -> str:
    """Build a SQL expression that maps legacy markers to supported variables."""
    expression = column
    replacements = (
        ("[Business Name]", "{{org.name}}"),
        ("[Company Name]", "{{org.name}}"),
        ("[Organization Name]", "{{org.name}}"),
        ("[Org Name]", "{{org.name}}"),
        ("[Agent Name]", "{{agent.name}}"),
        ("{{organization.name}}", "{{org.name}}"),
        ("{{business.name}}", "{{org.name}}"),
        ("{{company.name}}", "{{org.name}}"),
        ("{{organization.industry}}", "{{org.industry}}"),
        ("{{organization.location}}", "{{org.location}}"),
        ("{{organization.business_details}}", "{{org.business_details}}"),
    )
    for old, new in replacements:
        expression = f"REPLACE({expression}, '{old}', '{new}')"
    return expression


def upgrade() -> None:
    """Rewrite legacy template markers in every prompt-bearing text column."""
    columns = (
        "description",
        "persona",
        "tone",
        "mission",
        "greeting",
        "custom_instructions",
    )
    assignments = ",\n          ".join(
        f"{column} = {_canonicalize(column)}" for column in columns
    )
    op.execute(
        f"""
        UPDATE voice_templates
        SET {assignments}
        WHERE description IS NOT NULL
           OR persona IS NOT NULL
           OR tone IS NOT NULL
           OR mission IS NOT NULL
           OR greeting IS NOT NULL
           OR custom_instructions IS NOT NULL
        """
    )


def downgrade() -> None:
    """Do not reintroduce ambiguous legacy placeholder syntax."""
    pass
