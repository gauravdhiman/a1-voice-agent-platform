"""Rename legacy Google Calendar catalog entries to appointment names.

This migration is retained in the canonical branch because it was applied to
the staging database before the appointment-contract implementation replaced
the earlier prototype.  It contains catalog-history changes only; the runtime
implementation lives in the appointment service and adapters.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "20260817000002"
down_revision: Union[str, None] = "20260817000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Rename legacy rows when the appointment-specific names are unused."""
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM platform_tools WHERE name = 'Google_calendar')
               AND EXISTS (SELECT 1 FROM platform_tools WHERE name = 'Google_calendar_appointment')
            THEN
                RAISE EXCEPTION
                    'Cannot rename Google_calendar: Google_calendar_appointment already exists';
            END IF;
            IF EXISTS (SELECT 1 FROM platform_tools WHERE name = 'Google_calendar_mcp')
               AND EXISTS (SELECT 1 FROM platform_tools WHERE name = 'Google_calendar_appointment_mcp')
            THEN
                RAISE EXCEPTION
                    'Cannot rename Google_calendar_mcp: Google_calendar_appointment_mcp already exists';
            END IF;
        END $$
        """
    )
    op.execute(
        """
        UPDATE platform_tools
        SET name = 'Google_calendar_appointment',
            description = 'Book and manage business appointments in Google Calendar, including availability, rescheduling, and cancellation.'
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
        SET name = 'Google_calendar_appointment_mcp',
            description = 'Book and manage business appointments in Google Calendar through the appointment MCP connector.'
        WHERE name = 'Google_calendar_mcp'
          AND NOT EXISTS (
              SELECT 1 FROM platform_tools
              WHERE name = 'Google_calendar_appointment_mcp'
          )
        """
    )


def downgrade() -> None:
    """Restore legacy names when the old names are not occupied."""
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
