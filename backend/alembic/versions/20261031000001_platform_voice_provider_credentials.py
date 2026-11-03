"""Add encrypted platform voice-provider credentials."""

import sqlalchemy as sa
from alembic import op

revision = "20261031000001"
down_revision = "20261030000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create one encrypted, independently upsertable row per provider."""
    op.create_table(
        "platform_voice_provider_credentials",
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column(
            "credential_encrypted",
            sa.Text(),
            nullable=False,
            comment="Fernet-encrypted JSON containing the platform API key.",
        ),
        sa.Column("updated_by", sa.UUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "provider IN ('google', 'deepgram', 'openai', 'cartesia', "
            "'cerebras', 'openrouter', 'fish')",
            name="ck_platform_voice_provider_credentials_provider",
        ),
        sa.PrimaryKeyConstraint("provider"),
    )
    op.execute(
        "ALTER TABLE platform_voice_provider_credentials ENABLE ROW LEVEL SECURITY"
    )
    op.execute(
        "REVOKE ALL ON TABLE platform_voice_provider_credentials "
        "FROM anon, authenticated"
    )
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE "
        "ON TABLE platform_voice_provider_credentials TO service_role"
    )
    op.execute("""
        CREATE POLICY "Service role manages platform voice credentials"
        ON platform_voice_provider_credentials
        FOR ALL
        TO service_role
        USING (true)
        WITH CHECK (true)
        """)


def downgrade() -> None:
    """Drop the new credentials table."""
    op.execute(
        'DROP POLICY IF EXISTS "Service role manages platform voice credentials" '
        "ON platform_voice_provider_credentials"
    )
    op.drop_table("platform_voice_provider_credentials")
