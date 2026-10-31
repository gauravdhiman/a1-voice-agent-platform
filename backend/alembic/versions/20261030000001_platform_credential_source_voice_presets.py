"""Add credential sources and selectable platform defaults to voice presets."""

import sqlalchemy as sa

from alembic import op

revision = "20261030000001"
down_revision = "20261019000005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Mark the current default as a published platform preset and add RPC."""
    op.add_column(
        "pipeline_presets",
        sa.Column(
            "credential_source",
            sa.String(length=20),
            server_default=sa.text("'organization'"),
            nullable=False,
            comment=(
                "Credential boundary: platform provider keys or organization "
                "credentials."
            ),
        ),
    )
    op.execute(
        "UPDATE public.pipeline_presets "
        "SET credential_source = 'platform', is_published = true, "
        "description = 'Platform-managed profile used when no voice profile is selected.' "
        "WHERE is_default = true"
    )
    op.create_check_constraint(
        "ck_pipeline_presets_credential_source",
        "pipeline_presets",
        "credential_source IN ('platform', 'organization')",
    )
    op.create_check_constraint(
        "ck_pipeline_presets_default_platform_published",
        "pipeline_presets",
        "NOT is_default OR (credential_source = 'platform' AND is_published)",
    )
    op.execute("""
        CREATE FUNCTION public.set_default_pipeline_preset(p_preset_id uuid)
        RETURNS void
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = public, pg_temp
        AS $set_default$
        DECLARE
            v_credential_source text;
            v_is_published boolean;
        BEGIN
            LOCK TABLE public.pipeline_presets IN EXCLUSIVE MODE;
            SELECT credential_source, is_published
              INTO v_credential_source, v_is_published
              FROM public.pipeline_presets
             WHERE id = p_preset_id
             FOR UPDATE;
            IF NOT FOUND THEN
                RAISE EXCEPTION 'Preset not found' USING ERRCODE = 'P0002';
            END IF;
            IF v_credential_source <> 'platform' THEN
                RAISE EXCEPTION 'Only platform presets can be the default'
                    USING ERRCODE = '23514';
            END IF;
            IF NOT v_is_published THEN
                RAISE EXCEPTION 'Only published presets can be the default'
                    USING ERRCODE = '23514';
            END IF;

            UPDATE public.pipeline_presets
               SET is_default = false, updated_at = now()
             WHERE is_default = true AND id <> p_preset_id;
            UPDATE public.pipeline_presets
               SET is_default = true, updated_at = now()
             WHERE id = p_preset_id;
        END
        $set_default$;
        REVOKE ALL ON FUNCTION public.set_default_pipeline_preset(uuid)
            FROM PUBLIC, anon, authenticated;
        GRANT EXECUTE ON FUNCTION public.set_default_pipeline_preset(uuid)
            TO service_role;
        """)


def downgrade() -> None:
    """Preserve source/default semantics; this migration is forward-only."""
    raise RuntimeError("Voice preset credential sources require a forward repair")
