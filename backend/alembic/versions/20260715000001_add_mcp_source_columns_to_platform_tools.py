"""add_mcp_source_columns_to_platform_tools

Additive columns that let a ``platform_tools`` row point at a remote MCP server
(Streamable HTTP) instead of an in-tree ``BaseTool``. This is Phase 2 of the
MCP integration (see ``docs/03_implementation/mcp_integration_rfc.md``).

Coexistence (RFC §1.1): every existing row defaults to ``tool_source='legacy'``
so the original ``LiveKitToolRegistry`` path keeps working unchanged. The MCP
path is only taken for rows explicitly marked ``tool_source='mcp'``. No legacy
column or behavior is removed.

Revision ID: 20260715000001
Revises: 20260705000001
Create Date: 2026-07-15 00:00:01.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20260715000001"
down_revision: Union[str, None] = "20260705000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add MCP-source columns to platform_tools (all additive, reversible)."""
    op.add_column(
        "platform_tools",
        sa.Column(
            "tool_source",
            sa.String(length=20),
            server_default="legacy",
            nullable=False,
            comment=(
                "Where the tool implementation lives: 'legacy' (in-tree BaseTool "
                "via LiveKitToolRegistry) or 'mcp' (remote MCP server)."
            ),
        ),
    )
    op.add_column(
        "platform_tools",
        sa.Column(
            "mcp_server_url",
            sa.String(length=1024),
            nullable=True,
            comment=(
                "Streamable HTTP endpoint of the MCP server (e.g. "
                "'https://host/mcp'). Used only when tool_source='mcp'."
            ),
        ),
    )
    op.add_column(
        "platform_tools",
        sa.Column(
            "mcp_server_headers",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment=(
                "Static headers sent on every MCP request (server-level auth). "
                "Per-org user OAuth tokens are injected at call time."
            ),
        ),
    )
    op.add_column(
        "platform_tools",
        sa.Column(
            "mcp_server_name",
            sa.String(length=200),
            nullable=True,
            comment=(
                "Human-readable MCP server name for logging/labels. Defaults to "
                "the tool name when unset. Used only when tool_source='mcp'."
            ),
        ),
    )


def downgrade() -> None:
    """Drop the MCP-source columns (restores the pre-Phase-2 schema)."""
    op.drop_column("platform_tools", "mcp_server_name")
    op.drop_column("platform_tools", "mcp_server_headers")
    op.drop_column("platform_tools", "mcp_server_url")
    op.drop_column("platform_tools", "tool_source")