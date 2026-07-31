"""add_pipeline_presets_and_org_provider_credentials

Phase 3 of the modular voice engine (see
``docs/01_architecture/voice_engine_pipeline_design.md``). Makes the pipeline
usable by agents via **platform-admin-managed presets** and consolidates all
per-org provider credentials into one encrypted blob.

Three changes, all additive:

1. **New ``pipeline_presets`` table** — a global, platform-admin-managed catalog
   (no RLS, like ``platform_tools``). Each row is a named voice-engine preset
   whose ``config`` JSONB holds a validated ``SpeechConfig`` (realtime or
   pipeline discriminated union — see ``shared/voice_agents/speech_config.py``).
   ``preset_type`` is a denormalized filter column derived from
   ``config.engine_mode`` on every write (kept in sync by the service, never set
   by hand). ``is_published`` is the draft↔published lifecycle (FALSE = draft,
   platform-admin-only; TRUE = visible to all org users for assignment). **No
   versioning** — the worker fetches the preset row live on every call, so admin
   edits take effect on the next call.

2. **``voice_agents.preset_id``** — nullable FK to ``pipeline_presets.id`` with
   ``ON DELETE SET NULL``. An agent references one preset; the worker loads it
   live each call. ``NULL`` (legacy agents) → the worker falls back to
   ``default_realtime_config()`` (today's realtime behavior, unchanged).

3. **``organizations.provider_credentials``** — Fernet-encrypted JSON blob
   holding ALL per-org provider keys: ``{google, deepgram, openai, cartesia,
   cerebras, livekit: {api_key, api_secret}}`` (only the set keys present).
   Consolidates the previously-plaintext ``organizations.google_api_key`` (a
   latent security gap — it was stored unencrypted despite its docstring) and
   adds storage for the new direct-provider + LiveKit Inference keys. The
   ``google_api_key`` column is **retained but no longer the source of truth**;
   a follow-up migration drops it once the encrypted path is verified.

Backfill: every org with a non-null ``google_api_key`` has it encrypted into
``provider_credentials['google']`` via ``encrypt_data`` (requires ``ENCRYPTION_KEY``
in the env at run time; the dev fallback is deterministic).

Revision ID: 20260729000001
Revises: 20260726000001
Create Date: 2026-07-29 00:00:01.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20260729000001"
down_revision: Union[str, None] = "20260726000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create pipeline_presets, add voice_agents.preset_id and
    organizations.provider_credentials, and backfill google_api_key."""
    # 1. pipeline_presets table — global platform catalog (no RLS, like
    #    platform_tools).
    op.create_table(
        "pipeline_presets",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "preset_type",
            sa.String(length=20),
            nullable=False,
            comment=(
                "Denormalized from config.engine_mode on every write "
                "(realtime|pipeline). Filter column for listings; the service "
                "keeps it in sync — never set by hand."
            ),
        ),
        sa.Column(
            "config",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            comment=(
                "Validated SpeechConfig JSONB (realtime or pipeline "
                "discriminated union). See shared/voice_agents/speech_config.py."
            ),
        ),
        sa.Column(
            "is_published",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
            comment=(
                "Publish lifecycle: FALSE = draft (platform-admin-only), TRUE "
                "= published to the global catalog (assignable by org admins)."
            ),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(
        "ix_pipeline_presets_is_published",
        "pipeline_presets",
        ["is_published"],
    )

    # 2. voice_agents.preset_id — FK to pipeline_presets, SET NULL on delete so
    #    deleting a preset drops referencing agents back to the realtime default.
    op.add_column(
        "voice_agents",
        sa.Column(
            "preset_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            nullable=True,
            comment=(
                "FK to pipeline_presets.id. The worker loads this preset live "
                "each call. NULL = legacy agent -> realtime default config."
            ),
        ),
    )
    op.create_foreign_key(
        "voice_agents_preset_id_fkey",
        "voice_agents",
        "pipeline_presets",
        ["preset_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_voice_agents_preset_id", "voice_agents", ["preset_id"])

    # 3. organizations.provider_credentials — encrypted JSON blob of all
    #    per-org provider keys. Replaces the plaintext google_api_key as the
    #    source of truth (that column is retained but unused; dropped later).
    op.add_column(
        "organizations",
        sa.Column(
            "provider_credentials",
            sa.Text(),
            nullable=True,
            comment=(
                "Fernet-encrypted JSON of per-org provider keys via "
                "encrypt_data/decrypt_data: {google, deepgram, openai, "
                "cartesia, cerebras, livekit: {api_key, api_secret}}. The "
                "worker's key_resolver decrypts this to build the api_keys map."
            ),
        ),
    )

    # Backfill: move existing plaintext google_api_key into the encrypted blob.
    # Requires ENCRYPTION_KEY in the env (set in dev/prod; dev fallback is
    # deterministic). The google_api_key column is retained for rollback safety.
    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            "SELECT id, google_api_key FROM organizations "
            "WHERE google_api_key IS NOT NULL"
        )
    ).fetchall()
    if rows:
        # Deferred import so the migration module doesn't pull shared at import
        # time (keeps `alembic history`/offline use light); only needed when
        # actually backfilling online.
        from shared.common.security import encrypt_data

        for org_id, google_key in rows:
            bind.execute(
                sa.text(
                    "UPDATE organizations SET provider_credentials = :enc "
                    "WHERE id = :oid"
                ),
                {"enc": encrypt_data({"google": google_key}), "oid": org_id},
            )


def downgrade() -> None:
    """Drop provider_credentials, preset_id, and the pipeline_presets table.

    Note: the google_api_key backfill is NOT reversed (its column is retained
    and was never modified), so existing plaintext values are still present.
    """
    op.drop_column("organizations", "provider_credentials")
    op.drop_index("ix_voice_agents_preset_id", table_name="voice_agents")
    op.drop_constraint(
        "voice_agents_preset_id_fkey",
        "voice_agents",
        type_="foreignkey",
    )
    op.drop_column("voice_agents", "preset_id")
    op.drop_index(
        "ix_pipeline_presets_is_published", table_name="pipeline_presets"
    )
    op.drop_table("pipeline_presets")