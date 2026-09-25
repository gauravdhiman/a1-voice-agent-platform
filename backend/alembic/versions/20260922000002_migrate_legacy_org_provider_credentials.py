"""Clear legacy plaintext organization provider credentials.

The earlier provider-credentials migration copied ``google_api_key`` into the
encrypted blob but intentionally left the legacy column in place for rollback
safety. This release completes the data-hardening step by preserving any
existing encrypted providers, adding the legacy Google value only when needed,
and clearing the plaintext column.

The column is intentionally not dropped here. Older application instances can
still exist during a rolling deployment, and dropping it would make those
instances fail when they write an organization update. A later cleanup
migration can remove the empty compatibility column after the old code path is
no longer deployable.

Revision ID: 20260922000002
Revises: 20260922000001
Create Date: 2026-09-22
"""

from typing import Any, Callable, Optional, Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260922000002"
down_revision: Union[str, None] = "20260922000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _migrate_credential_blob(
    existing_blob: Optional[str],
    legacy_google_key: Optional[str],
    decrypt: Callable[[str], dict[str, Any]],
    encrypt: Callable[[Optional[dict[str, Any]]], str],
) -> Optional[str]:
    """Return encrypted credentials while preserving existing providers."""
    credentials: dict[str, Any] = {}
    if existing_blob:
        credentials = decrypt(existing_blob)
        if not isinstance(credentials, dict) or not credentials:
            raise RuntimeError(
                "Unable to decrypt an existing organization provider-credentials "
                "payload; refusing to clear the legacy value"
            )

    if legacy_google_key and not credentials.get("google"):
        credentials["google"] = str(legacy_google_key)

    return encrypt(credentials) if credentials else None


def upgrade() -> None:
    """Encrypt any remaining legacy Google keys, then clear plaintext values."""
    from shared.common.security import decrypt_data, encrypt_data

    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            """
            SELECT id, google_api_key, provider_credentials
            FROM organizations
            WHERE google_api_key IS NOT NULL
            """
        )
    ).fetchall()

    for org_id, legacy_google_key, existing_blob in rows:
        encrypted = _migrate_credential_blob(
            str(existing_blob) if existing_blob else None,
            str(legacy_google_key) if legacy_google_key else None,
            decrypt_data,
            encrypt_data,
        )
        bind.execute(
            sa.text(
                """
                UPDATE organizations
                SET provider_credentials = :provider_credentials,
                    google_api_key = NULL
                WHERE id = :organization_id
                """
            ),
            {
                "organization_id": org_id,
                "provider_credentials": encrypted,
            },
        )


def downgrade() -> None:
    """Intentionally perform no plaintext rehydration during downgrade.

    Recreating plaintext credentials during rollback would undermine the
    security property this migration establishes. The compatibility column is
    retained, so a reviewed forward migration remains the supported rollback
    strategy for application code.
    """
