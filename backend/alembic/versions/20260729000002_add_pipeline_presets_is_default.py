"""add_pipeline_presets_is_default

Phase 4 of the modular voice engine (see
``docs/01_architecture/voice_engine_pipeline_design.md``). Promotes the
previously-hardcoded realtime fallback into a **managed system default preset**.

Before Phase 4, an agent with ``preset_id`` NULL (a legacy agent, or one whose
preset was deleted via the FK ``ON DELETE SET NULL``) resolved to the hardcoded
``default_realtime_config()`` (Gemini realtime) in the worker — invisible and
unmanageable. This migration makes that fallback a real, editable row:

- adds ``pipeline_presets.is_default`` (Boolean, NOT NULL, default FALSE);
- adds a **partial unique index** ``ux_pipeline_presets_is_default`` on
  ``is_default`` restricted to ``is_default = true``, enforcing at-most-one
  system default row;
- **seeds** the single system-default row (``name='System Default'``,
  ``is_default=true``, ``is_published=false``, ``preset_type='realtime'``,
  ``config = default_realtime_config().model_dump(mode='json')``) so out-of-box
  behavior is identical to the pre-Phase-4 hardcoded fallback.

The default is platform-admin-managed via dedicated endpoints (``GET``/
``PUT /api/v1/presets/default``); the service guards make it non-publishable
and non-deletable (immutable except its ``config``). It is never shown in the
org-admin picker (the picker lists published presets only). See
``shared/voice_agents/preset_service.py`` and ``docs/02_core_systems/voice_engine.md``.

Additive only (column + index + one seeded row).

Revision ID: 20260729000002
Revises: 20260729000001
Create Date: 2026-07-29 00:00:02.000000

"""

import json
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260729000002"
down_revision: Union[str, None] = "20260729000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Reserved name for the single system-default preset row (kept in sync with
# ``shared.voice_agents.preset_models.RESERVED_DEFAULT_NAME``). Duplicated here
# rather than imported so the migration module stays import-light (no ``shared``
# import at module load — ``alembic history``/offline use stay light; the
# ``default_realtime_config`` import is deferred to ``upgrade()`` for the same
# reason).
RESERVED_DEFAULT_NAME = "System Default"


def upgrade() -> None:
    """Add is_default, its partial unique index, and seed the default row."""
    op.add_column(
        "pipeline_presets",
        sa.Column(
            "is_default",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
            comment=(
                "TRUE only for the single system-default preset row — the "
                "fallback config an agent uses when it has no preset selected "
                "(preset_id NULL). Response-only; the service sets it only on "
                "this seeded row (never accepted as input)."
            ),
        ),
    )

    # Partial unique index: at most one row may have is_default = true.
    op.create_index(
        "ux_pipeline_presets_is_default",
        "pipeline_presets",
        ["is_default"],
        unique=True,
        postgresql_where=sa.text("is_default = true"),
    )

    # Seed the system-default row. Deferred import of default_realtime_config
    # so the migration module doesn't pull ``shared`` at import time (keeps
    # ``alembic history``/offline use light); only needed when seeding online.
    from shared.voice_agents.speech_config import default_realtime_config

    config_json = json.dumps(default_realtime_config().model_dump(mode="json"))

    bind = op.get_bind()
    # ON CONFLICT (name) DO NOTHING: idempotent — a pre-existing
    # "System Default" row (none from Phase 3, but defensively) is left intact
    # rather than clobbered. The partial unique index still guarantees at most
    # one is_default row.
    bind.execute(
        sa.text(
            "INSERT INTO pipeline_presets "
            "  (name, description, preset_type, config, is_default, "
            "   is_published, created_at, updated_at) "
            "VALUES "
            "  (:name, :desc, 'realtime', CAST(:config AS jsonb), true, false, "
            "   now(), now()) "
            "ON CONFLICT (name) DO NOTHING"
        ),
        {
            "name": RESERVED_DEFAULT_NAME,
            "desc": (
                "The fallback voice profile used when an agent has no voice "
                "profile selected. Managed by the platform admin via the "
                "default-preset editor; not publishable or deletable."
            ),
            "config": config_json,
        },
    )


def downgrade() -> None:
    """Drop the seeded default row, the partial unique index, and the column."""
    bind = op.get_bind()
    bind.execute(
        sa.text("DELETE FROM pipeline_presets WHERE name = :name"),
        {"name": RESERVED_DEFAULT_NAME},
    )
    op.drop_index("ux_pipeline_presets_is_default", table_name="pipeline_presets")
    op.drop_column("pipeline_presets", "is_default")
