"""Update the system default realtime preset to Gemini 3.8 Live.

Revision ID: 20260922000001
Revises: 20260920000001
Create Date: 2026-09-22
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260922000001"
down_revision: Union[str, None] = "20260920000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

OLD_MODEL = "gemini-2.5-flash-native-audio-preview-12-2025"
OLD_VOICE = "Puck"
NEW_MODEL = "gemini-3.8-live"
NEW_VOICE = "Zephyr"


def upgrade() -> None:
    """Set the existing system-default realtime row to Gemini 3.8 Live."""
    op.get_bind().execute(
        sa.text(
            """
            UPDATE pipeline_presets
            SET config = jsonb_set(
                    jsonb_set(
                        jsonb_set(
                            config,
                            '{provider}',
                            to_jsonb(CAST(:provider AS text)),
                            true
                        ),
                        '{model}',
                        to_jsonb(CAST(:model AS text)),
                        true
                    ),
                    '{voice}',
                    to_jsonb(CAST(:voice AS text)),
                    true
                ),
                updated_at = now()
            WHERE is_default = true
              AND preset_type = 'realtime'
              AND config->>'engine_mode' = 'realtime'
            """
        ),
        {"provider": "google", "model": NEW_MODEL, "voice": NEW_VOICE},
    )


def downgrade() -> None:
    """Restore old model/voice only if the default still has this migration's values."""
    op.get_bind().execute(
        sa.text(
            """
            UPDATE pipeline_presets
            SET config = jsonb_set(
                    jsonb_set(
                        config,
                        '{model}',
                        to_jsonb(CAST(:model AS text)),
                        true
                    ),
                    '{voice}',
                    to_jsonb(CAST(:voice AS text)),
                    true
                ),
                updated_at = now()
            WHERE is_default = true
              AND preset_type = 'realtime'
              AND config->>'engine_mode' = 'realtime'
              AND config->>'provider' = 'google'
              AND config->>'model' = :current_model
              AND config->>'voice' = :current_voice
            """
        ),
        {
            "model": OLD_MODEL,
            "voice": OLD_VOICE,
            "current_model": NEW_MODEL,
            "current_voice": NEW_VOICE,
        },
    )
