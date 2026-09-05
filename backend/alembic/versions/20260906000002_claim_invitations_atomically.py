"""Add an atomic, email-bound invitation claim function.

Invitation admission is part of the closed-signup security boundary. The
function locks the invitation row, verifies the invited email and pending
state, inserts an idempotent organization membership, and accepts the
invitation in one database transaction.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "20260906000002"
down_revision: Union[str, None] = "20260906000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the service-role-only invitation claim RPC."""
    op.execute(
        """
        CREATE OR REPLACE FUNCTION claim_invitation(
            p_token text,
            p_user_id uuid,
            p_email text
        )
        RETURNS jsonb
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = public
        AS $$
        DECLARE
            v_id uuid;
            v_email text;
            v_organization_id uuid;
            v_invited_by uuid;
            v_token text;
            v_status text;
            v_expires_at timestamptz;
            v_created_at timestamptz;
            v_accepted_at timestamptz;
            v_organization_name text;
            v_role_id uuid;
            v_now timestamptz;
        BEGIN
            IF p_user_id IS NULL
               OR p_token IS NULL
               OR btrim(p_token) = ''
               OR p_email IS NULL
               OR btrim(p_email) = '' THEN
                RETURN jsonb_build_object('success', false, 'error', 'invalid_request');
            END IF;

            SELECT
                i.id,
                i.email,
                i.organization_id,
                i.invited_by,
                i.token,
                i.status,
                i.expires_at,
                i.created_at,
                i.accepted_at,
                o.name
            INTO
                v_id,
                v_email,
                v_organization_id,
                v_invited_by,
                v_token,
                v_status,
                v_expires_at,
                v_created_at,
                v_accepted_at,
                v_organization_name
            FROM invitations AS i
            JOIN organizations AS o ON o.id = i.organization_id
            WHERE i.token = p_token
            FOR UPDATE OF i;

            IF NOT FOUND THEN
                RETURN jsonb_build_object('success', false, 'error', 'invitation_not_found');
            END IF;

            IF lower(btrim(v_email)) <> lower(btrim(p_email)) THEN
                RETURN jsonb_build_object('success', false, 'error', 'invitation_email_mismatch');
            END IF;

            IF v_status = 'accepted' THEN
                IF EXISTS (
                    SELECT 1
                    FROM user_roles
                    WHERE user_id = p_user_id
                      AND organization_id = v_organization_id
                ) THEN
                    RETURN jsonb_build_object(
                        'success', true,
                        'already_claimed', true,
                        'invitation', jsonb_build_object(
                            'id', v_id,
                            'email', v_email,
                            'organization_id', v_organization_id,
                            'invited_by', v_invited_by,
                            'token', v_token,
                            'status', 'accepted',
                            'expires_at', v_expires_at,
                            'created_at', v_created_at,
                            'accepted_at', v_accepted_at,
                            'organization_name', v_organization_name
                        )
                    );
                END IF;
                RETURN jsonb_build_object('success', false, 'error', 'invitation_already_accepted');
            END IF;

            IF v_status <> 'pending' THEN
                RETURN jsonb_build_object('success', false, 'error', 'invitation_not_pending');
            END IF;

            IF v_expires_at <= now() THEN
                UPDATE invitations
                SET status = 'expired'
                WHERE id = v_id AND status = 'pending';
                RETURN jsonb_build_object('success', false, 'error', 'invitation_expired');
            END IF;

            SELECT id INTO v_role_id
            FROM roles
            WHERE name = 'regular_user'
            LIMIT 1;

            IF v_role_id IS NULL THEN
                RETURN jsonb_build_object('success', false, 'error', 'role_not_found');
            END IF;

            INSERT INTO user_roles (user_id, role_id, organization_id)
            VALUES (p_user_id, v_role_id, v_organization_id)
            ON CONFLICT (user_id, organization_id) DO NOTHING;

            v_now := now();
            UPDATE invitations
            SET status = 'accepted', accepted_at = v_now
            WHERE id = v_id AND status = 'pending';

            v_accepted_at := v_now;
            RETURN jsonb_build_object(
                'success', true,
                'already_claimed', false,
                'invitation', jsonb_build_object(
                    'id', v_id,
                    'email', v_email,
                    'organization_id', v_organization_id,
                    'invited_by', v_invited_by,
                    'token', v_token,
                    'status', 'accepted',
                    'expires_at', v_expires_at,
                    'created_at', v_created_at,
                    'accepted_at', v_accepted_at,
                    'organization_name', v_organization_name
                )
            );
        END;
        $$;
        """
    )
    op.execute("REVOKE ALL ON FUNCTION claim_invitation(text, uuid, text) FROM PUBLIC")
    op.execute(
        "GRANT EXECUTE ON FUNCTION claim_invitation(text, uuid, text) TO service_role"
    )


def downgrade() -> None:
    """Remove the invitation claim RPC."""
    op.execute("DROP FUNCTION IF EXISTS claim_invitation(text, uuid, text)")
