"""Add the canonical Google Calendar appointment tool catalog entries.

The native row is backed by the shared in-tree implementation.  The MCP row is
backed by the platform-owned REST connector that runs alongside voice-ws.  Both
rows use the same OAuth metadata and appointment contract; the separate names
let organizations choose the runtime path without confusing it with generic
calendar or journal management.
"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "20260818000001"
down_revision: Union[str, None] = "20260817000002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_AUTH_CONFIG = """
{
  "provider": "google",
  "scopes": [
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/calendar.readonly"
  ],
  "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
  "token_url": "https://oauth2.googleapis.com/token",
  "access_type": "offline",
  "prompt": "consent",
  "pkce_supported": true
}
""".strip()

_CONFIG_SCHEMA = """
{
  "type": "object",
  "properties": {
    "calendar_id": {"type": "string", "default": "primary"},
    "timezone": {"type": ["string", "null"]},
    "require_phone": {"type": "boolean", "default": false},
    "require_email": {"type": "boolean", "default": false}
  }
}
""".strip()


def upgrade() -> None:
    """Create or canonicalize both appointment tool catalog rows idempotently."""
    # Preserve existing attachments from the earlier generic names when the
    # destination name is not already present.  No agent_tools rows are copied
    # or deleted; their foreign-key identity remains stable.
    op.execute(
        """
        UPDATE platform_tools
        SET name = 'Google_calendar_appointment'
        WHERE name = 'Google_calendar'
          AND NOT EXISTS (
              SELECT 1 FROM platform_tools
              WHERE name = 'Google_calendar_appointment'
          )
        """
    )
    op.execute(
        """
        UPDATE platform_tools
        SET name = 'Google_calendar_appointment_mcp'
        WHERE name = 'Google_calendar_mcp'
          AND NOT EXISTS (
              SELECT 1 FROM platform_tools
              WHERE name = 'Google_calendar_appointment_mcp'
          )
        """
    )

    op.execute(
        text(
            """
        INSERT INTO platform_tools (
            name, description, config_schema, is_active, requires_auth,
            auth_type, auth_config, tool_source, is_published, is_premium
        ) VALUES (
            'Google_calendar_appointment',
            'Find availability and book, update, or cancel business appointments on an organization''s Google Calendar.',
            CAST(:config_schema AS jsonb),
            TRUE,
            TRUE,
            'oauth2',
            CAST(:auth_config AS jsonb),
            'legacy',
            TRUE,
            FALSE
        )
        ON CONFLICT (name) DO UPDATE SET
            description = EXCLUDED.description,
            config_schema = EXCLUDED.config_schema,
            is_active = TRUE,
            requires_auth = TRUE,
            auth_type = 'oauth2',
            auth_config = EXCLUDED.auth_config,
            tool_source = 'legacy',
            is_published = TRUE
            """
        ).bindparams(config_schema=_CONFIG_SCHEMA, auth_config=_AUTH_CONFIG)
    )
    op.execute(
        text(
            """
        INSERT INTO platform_tools (
            name, description, config_schema, is_active, requires_auth,
            auth_type, auth_config, tool_source, mcp_server_url,
            mcp_server_name, is_published, is_premium
        ) VALUES (
            'Google_calendar_appointment_mcp',
            'Google Calendar Appointment via the platform-owned MCP connector.',
            CAST(:config_schema AS jsonb),
            TRUE,
            TRUE,
            'oauth2',
            CAST(:auth_config AS jsonb),
            'mcp',
            'http://127.0.0.1:8733/mcp',
            'google-calendar-appointment',
            TRUE,
            FALSE
        )
        ON CONFLICT (name) DO UPDATE SET
            description = EXCLUDED.description,
            config_schema = EXCLUDED.config_schema,
            is_active = TRUE,
            requires_auth = TRUE,
            auth_type = 'oauth2',
            auth_config = EXCLUDED.auth_config,
            tool_source = 'mcp',
            mcp_server_url = EXCLUDED.mcp_server_url,
            mcp_server_name = EXCLUDED.mcp_server_name,
            is_published = TRUE
            """
        ).bindparams(config_schema=_CONFIG_SCHEMA, auth_config=_AUTH_CONFIG)
    )


def downgrade() -> None:
    """Restore legacy names only when no pre-existing row would collide."""
    op.execute(
        """
        UPDATE platform_tools
        SET name = 'Google_calendar_mcp'
        WHERE name = 'Google_calendar_appointment_mcp'
          AND NOT EXISTS (
              SELECT 1 FROM platform_tools
              WHERE name = 'Google_calendar_mcp'
          )
        """
    )
    op.execute(
        """
        UPDATE platform_tools
        SET name = 'Google_calendar'
        WHERE name = 'Google_calendar_appointment'
          AND NOT EXISTS (
              SELECT 1 FROM platform_tools
              WHERE name = 'Google_calendar'
          )
        """
    )
