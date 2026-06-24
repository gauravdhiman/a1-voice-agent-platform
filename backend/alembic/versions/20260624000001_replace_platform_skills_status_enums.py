"""replace is_active/is_deleted with single status enum on platform_skills

Revision ID: 20260624000001
Revises: 20260623000001
Create Date: 2026-06-24 00:00:01.000000

Consolidates ``is_active`` and ``is_deleted`` booleans into a single
``status VARCHAR(20)`` column with a CHECK constraint enumerating the
allowed values:

    draft, active, deprecated, deleted

Backfill mapping (matches the Pydantic state machine in
``shared/voice_agents/skill_models.PlatformSkillStatus``):

    is_deleted = TRUE                          -> 'deleted'
    is_deleted = FALSE AND is_active = FALSE   -> 'deprecated'
    is_deleted = FALSE AND is_active = TRUE    -> 'active'
    default for new rows                       -> 'active'

After the backfill, ``is_active`` and ``is_deleted`` are dropped. All reads
should switch to ``status`` and the application layer enforces the state
machine via dedicated transition endpoints (deprecate/reactivate/delete/
restore) instead of letting callers flip the field through generic update
endpoints.

The migration is idempotent against the original schema: it works whether
the table has both columns (existing dev DB), only ``is_deleted`` (the
half-applied previous migration), or neither (fresh dev DB). The DOWN
migration recreates the two booleans with best-effort backfill so a
revert is safe.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260624000001"
down_revision: Union[str, None] = "20260623000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


VALID_STATUSES = ("draft", "active", "deprecated", "deleted")


def _column_exists(table_name: str, column_name: str) -> bool:
    """Return True if ``table_name`` has a column named ``column_name``."""
    bind = op.get_bind()
    insp = sa.inspect(bind)
    return column_name in {c["name"] for c in insp.get_columns(table_name)}


def upgrade() -> None:
    # 1. Add the status column with a sensible default; tolerate re-runs.
    if not _column_exists("platform_skills", "status"):
        op.add_column(
            "platform_skills",
            sa.Column(
                "status",
                sa.String(length=20),
                nullable=False,
                server_default=sa.text("'active'"),
            ),
        )

    # 2. Backfill from the boolean flags if they exist. Use a single CASE so
    #    we don't double-set rows. The result is deterministic regardless of
    #    which of the two booleans exist when the migration runs.
    has_is_active = _column_exists("platform_skills", "is_active")
    has_is_deleted = _column_exists("platform_skills", "is_deleted")

    if has_is_active or has_is_deleted:
        # Build the CASE expression depending on which columns are present.
        # When is_deleted exists, it takes precedence (deleted trumps deprecated).
        when_clauses = []
        if has_is_deleted:
            when_clauses.append("WHEN is_deleted = TRUE THEN 'deleted'")
        if has_is_active:
            when_clauses.append("WHEN is_active = FALSE THEN 'deprecated'")
            when_clauses.append("WHEN is_active = TRUE THEN 'active'")
        when_clauses.append("ELSE 'active'")
        case_expr = " ".join(when_clauses)

        op.execute(
            sa.text(
                f"UPDATE platform_skills SET status = CASE {case_expr} END"
            )
        )

    # 3. Enforce the enum at the DB level via a CHECK constraint. We name it
    #    so downgrade can drop it explicitly.
    op.create_check_constraint(
        "platform_skills_status_valid",
        "platform_skills",
        f"status IN ({', '.join(repr(s) for s in VALID_STATUSES)})",
    )

    # 4. Drop the legacy booleans once status is populated + constrained.
    if has_is_deleted:
        op.drop_column("platform_skills", "is_deleted")
    if has_is_active:
        op.drop_column("platform_skills", "is_active")


def downgrade() -> None:
    # Drop the CHECK first so we can rewrite the column freely.
    op.drop_constraint(
        "platform_skills_status_valid", "platform_skills", type_="check"
    )

    # Recreate the two booleans with a best-effort backfill from status.
    if not _column_exists("platform_skills", "is_active"):
        op.add_column(
            "platform_skills",
            sa.Column(
                "is_active",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("true"),
            ),
        )
    if not _column_exists("platform_skills", "is_deleted"):
        op.add_column(
            "platform_skills",
            sa.Column(
                "is_deleted",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
        )

    # Best-effort reverse backfill (matches the original boolean semantics).
    op.execute(
        sa.text(
            "UPDATE platform_skills SET is_active = (status <> 'deprecated')"
        )
    )
    op.execute(
        sa.text("UPDATE platform_skills SET is_deleted = (status = 'deleted')")
    )

    op.drop_column("platform_skills", "status")
