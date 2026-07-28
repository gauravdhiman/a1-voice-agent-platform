"""add_is_published_to_platform_tools

Introduces the **publish lifecycle** for ``platform_tools`` (see
``docs/03_implementation/mcp_integration_rfc.md`` — "Platform-admin authoring +
publish lifecycle"). A custom MCP server is now authored by a **platform
admin**, tested in-memory, then **published** to the global catalog where any
org admin can attach it to their agents. This retires the org-scoped custom
tier (the ``organization_id`` column is kept but dormant).

One additive column on ``platform_tools``:

* ``is_published`` — BOOLEAN, NOT NULL, DEFAULT FALSE. ``FALSE`` = a draft
  visible only to platform admins (in the authoring/management view);
  ``TRUE`` = published to the global catalog, visible to all org users in the
  agent tool panel (combined with the existing ``is_active`` flag).
  ``get_platform_tools`` filters by ``is_published`` for org users
  (published-only) and returns all rows (drafts + published) for platform
  admins via ``include_drafts=True``.

Backfill: every existing row (Google Calendar, Gmail, CalCom, Google Sheets,
Google_calendar, and any legacy rows) is set ``is_published = TRUE`` so the
live catalog is unaffected — these were already globally visible and remain
so. New MCP servers created from the UI start as drafts and must be explicitly
published.

Revision ID: 20260726000001
Revises: 20260725000001
Create Date: 2026-07-26 00:00:01.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260726000001"
down_revision: Union[str, None] = "20260725000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add is_published to platform_tools and backfill existing rows to TRUE."""
    op.add_column(
        "platform_tools",
        sa.Column(
            "is_published",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
            comment=(
                "Publish lifecycle: FALSE = draft (platform-admin-only), "
                "TRUE = published to the global catalog (visible to all org "
                "users in the tool panel, combined with is_active). Custom MCP "
                "servers are authored by platform admins, tested, then "
                "published. See docs/03_implementation/mcp_integration_rfc.md."
            ),
        ),
    )

    # Backfill: preserve the live catalog — every existing row was already
    # globally visible, so it starts published. New UI-created MCP servers
    # default to FALSE (draft) and must be explicitly published.
    op.execute("UPDATE platform_tools SET is_published = TRUE")

    # Org-user listing filters on is_published; index it.
    op.create_index(
        "ix_platform_tools_is_published",
        "platform_tools",
        ["is_published"],
    )


def downgrade() -> None:
    """Drop the is_published column."""
    op.drop_index(
        "ix_platform_tools_is_published", table_name="platform_tools"
    )
    op.drop_column("platform_tools", "is_published")