"""add_org_scope_and_mcp_secret_headers_to_platform_tools

Lets an end-user configure a custom remote MCP server from the UI (see
``docs/03_implementation/mcp_integration_rfc.md`` — "Configure from UI"). Two
additive columns on ``platform_tools``:

* ``organization_id`` — NULL means the global curated catalog (platform-admin
  managed, the existing model); a set value means an org-scoped custom server
  created by that org. ``get_platform_tools`` returns global rows ∪ the
  caller's org's rows so custom servers stay isolated per tenant. This is
  data isolation, not the permission policy (which is deferred).
* ``mcp_server_secret_headers`` — Fernet-encrypted JSON of server-level
  secret headers (e.g. an API key), stored as TEXT. Kept separate from the
  existing plaintext ``mcp_server_headers`` JSONB (non-secret static headers)
  so secrets are encrypted at rest. The worker decrypts and merges public +
  secret + per-user bearer at call time.

Both columns are nullable/additive — existing rows (NULL org = global, NULL
secret headers) keep working unchanged.

Revision ID: 20260725000001
Revises: 20260715000001
Create Date: 2026-07-25 00:00:01.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260725000001"
down_revision: Union[str, None] = "20260715000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add organization_id and mcp_server_secret_headers to platform_tools."""
    op.add_column(
        "platform_tools",
        sa.Column(
            "organization_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            nullable=True,
            comment=(
                "NULL = global curated catalog (platform-admin). Set = "
                "org-scoped custom MCP server created by that org. Used to "
                "isolate user-configured custom servers per tenant."
            ),
        ),
    )
    op.create_foreign_key(
        "platform_tools_organization_id_fkey",
        "platform_tools",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_platform_tools_organization_id",
        "platform_tools",
        ["organization_id"],
    )
    op.add_column(
        "platform_tools",
        sa.Column(
            "mcp_server_secret_headers",
            sa.Text(),
            nullable=True,
            comment=(
                "Encrypted JSON of server-level secret headers (e.g. an API "
                "key). Encrypted with Fernet via encrypt_data/decrypt_data. "
                "Merged with mcp_server_headers (public) and the per-user "
                "OAuth bearer at call time. Never returned to the frontend "
                "in plaintext."
            ),
        ),
    )


def downgrade() -> None:
    """Drop the org-scope and secret-headers columns."""
    op.drop_column("platform_tools", "mcp_server_secret_headers")
    op.drop_index("ix_platform_tools_organization_id", table_name="platform_tools")
    op.drop_constraint(
        "platform_tools_organization_id_fkey",
        "platform_tools",
        type_="foreignkey",
    )
    op.drop_column("platform_tools", "organization_id")