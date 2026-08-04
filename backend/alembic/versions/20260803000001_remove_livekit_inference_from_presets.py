"""Migrate deprecated livekit_inference pipeline stages to direct providers.

Revision ID: 20260803000001
Revises: 20260731000001
Create Date: 2026-08-03

LiveKit Inference presets are removed from the product. Existing preset rows
that still reference ``livekit_inference`` on a pipeline stage are rewritten to
direct provider keys (deepgram / openai / cartesia) so agents keep working on
Pipecat voice-ws without LiveKit Cloud.
"""

from __future__ import annotations

import json
from typing import Any

from alembic import op
from sqlalchemy import text

revision = "20260803000001"
down_revision = "20260731000001"
branch_labels = None
depends_on = None

_STAGE_DEFAULTS = {
    "stt": "deepgram",
    "llm": "openai",
    "tts": "cartesia",
}


def _normalize_config(config: dict[str, Any]) -> dict[str, Any]:
    if config.get("engine_mode") != "pipeline":
        return config
    updated = dict(config)
    for stage in ("stt", "llm", "tts"):
        stage_cfg = updated.get(stage)
        if not isinstance(stage_cfg, dict):
            continue
        if stage_cfg.get("provider") == "livekit_inference":
            stage_cfg = dict(stage_cfg)
            stage_cfg["provider"] = _STAGE_DEFAULTS[stage]
            updated[stage] = stage_cfg
    return updated


def upgrade() -> None:
    conn = op.get_bind()
    rows = conn.execute(
        text(
            "SELECT id, config FROM pipeline_presets "
            "WHERE config::text LIKE :pattern"
        ),
        {"pattern": "%livekit_inference%"},
    ).fetchall()
    for preset_id, config in rows:
        if isinstance(config, str):
            config_obj = json.loads(config)
        else:
            config_obj = config
        normalized = _normalize_config(config_obj)
        if normalized != config_obj:
            conn.execute(
                text(
                    "UPDATE pipeline_presets SET config = CAST(:config AS jsonb) "
                    "WHERE id = :id"
                ),
                {"config": json.dumps(normalized), "id": str(preset_id)},
            )


def downgrade() -> None:
    # Data migration is one-way; restoring livekit_inference would require
    # archived preset backups.
    pass
