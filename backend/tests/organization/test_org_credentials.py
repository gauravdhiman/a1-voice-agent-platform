"""Tests for the encrypted ``provider_credentials`` blob (Phase 3).

Covers the organization-service write path (a Google key supplied via the
legacy ``google_api_key`` field is validated, encrypted into
``provider_credentials["google"]``, and the plaintext column is cleared) and
the read path (``_organization_from_dict`` resolves the Google key back out of
the decrypted blob, falling back to the plaintext column for un-migrated rows).
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.organization.models import OrganizationUpdate
from src.organization.service import OrganizationService


@pytest.fixture
def organization_service(mock_supabase_client):
    """Create an OrganizationService wired to the mocked Supabase client."""
    with patch("shared.organization.service.supabase_config") as mock_config:
        mock_config.client = mock_supabase_client
        return OrganizationService()


def _row(org_id, *, provider_credentials=None, google_api_key=None):
    """Build a raw organizations row dict as Supabase would return it."""
    now = datetime.now(timezone.utc).isoformat()
    return {
        "id": str(org_id),
        "name": "Test Org",
        "description": "A test org",
        "slug": "test-org",
        "website": "https://test.org",
        "is_active": True,
        "industry": "Tech",
        "location": "Global",
        "business_details": None,
        "google_api_key": google_api_key,
        "provider_credentials": provider_credentials,
        "onboarding_completed": False,
        "created_at": now,
        "updated_at": now,
    }


class TestOrgProviderCredentialsWrite:
    """update_organization routes the Google key into the encrypted blob."""

    @pytest.mark.asyncio
    async def test_google_key_encrypted_and_plaintext_cleared(
        self, organization_service, mock_supabase_client
    ):
        org_id = uuid4()

        # Existing-row select returns no blob yet.
        existing_resp = MagicMock()
        existing_resp.data = [{"provider_credentials": None}]
        # Update returns the updated row with the new encrypted blob + cleared
        # plaintext column.
        updated_resp = MagicMock()
        updated_resp.data = [
            _row(org_id, provider_credentials="ENC_BLOB", google_api_key=None)
        ]

        table_mock = mock_supabase_client.table.return_value
        table_mock.execute.side_effect = [existing_resp, updated_resp]

        # validate_google_api_key is a real HTTP call — stub it as valid.
        organization_service.validate_google_api_key = AsyncMock(
            return_value=(True, None)
        )

        with patch("src.organization.service.encrypt_data") as mock_enc, patch(
            "src.organization.service.decrypt_data"
        ) as mock_dec:
            mock_enc.return_value = "ENC_BLOB"
            mock_dec.return_value = {}

            result, error = await organization_service.update_organization(
                org_id, OrganizationUpdate(google_api_key="GEM_KEY_123")
            )

        assert error is None
        assert result is not None
        # encrypt_data was called with google merged into the blob.
        mock_enc.assert_called_once_with({"google": "GEM_KEY_123"})
        # The plaintext column is cleared in the update payload.
        update_call = table_mock.update.call_args
        assert update_call.args[0]["google_api_key"] is None
        assert update_call.args[0]["provider_credentials"] == "ENC_BLOB"

    @pytest.mark.asyncio
    async def test_empty_google_key_clears_provider(
        self, organization_service, mock_supabase_client
    ):
        org_id = uuid4()

        existing_resp = MagicMock()
        existing_resp.data = [{"provider_credentials": "OLD_BLOB"}]
        updated_resp = MagicMock()
        updated_resp.data = [
            _row(org_id, provider_credentials=None, google_api_key=None)
        ]

        table_mock = mock_supabase_client.table.return_value
        table_mock.execute.side_effect = [existing_resp, updated_resp]

        with patch("src.organization.service.encrypt_data") as mock_enc, patch(
            "src.organization.service.decrypt_data"
        ) as mock_dec:
            # Existing blob had only google; clearing it leaves nothing.
            mock_dec.return_value = {"google": "OLD_KEY"}
            mock_enc.return_value = "ENC_BLOB"

            result, error = await organization_service.update_organization(
                org_id, OrganizationUpdate(google_api_key="")
            )

        assert error is None
        # _merge_provider_credentials drops google and returns None (no creds
        # remain), so the column is set to NULL, not re-encrypted.
        mock_enc.assert_not_called()
        update_call = table_mock.update.call_args
        assert update_call.args[0]["provider_credentials"] is None
        assert update_call.args[0]["google_api_key"] is None

    @pytest.mark.asyncio
    async def test_provider_credentials_input_merged_with_google(
        self, organization_service, mock_supabase_client
    ):
        org_id = uuid4()

        existing_resp = MagicMock()
        existing_resp.data = [{"provider_credentials": "OLD_BLOB"}]
        updated_resp = MagicMock()
        updated_resp.data = [
            _row(org_id, provider_credentials="NEW_BLOB", google_api_key=None)
        ]

        table_mock = mock_supabase_client.table.return_value
        table_mock.execute.side_effect = [existing_resp, updated_resp]

        organization_service.validate_google_api_key = AsyncMock(
            return_value=(True, None)
        )

        captured = {}

        def fake_enc(creds):
            captured["creds"] = dict(creds)
            return "NEW_BLOB"

        with patch(
            "src.organization.service.encrypt_data", side_effect=fake_enc
        ), patch("src.organization.service.decrypt_data") as mock_dec:
            mock_dec.return_value = {"google": "OLD_KEY"}  # existing blob

            result, error = await organization_service.update_organization(
                org_id,
                OrganizationUpdate(
                    google_api_key="NEW_GEM",
                    provider_credentials_input={
                        "openai": "sk-xxx",
                        "livekit": {"api_key": "lk", "api_secret": "lks"},
                    },
                ),
            )

        assert error is None
        # The merge preserves the existing google? No — google is being
        # replaced with NEW_GEM, and openai/livekit are added.
        assert captured["creds"] == {
            "google": "NEW_GEM",
            "openai": "sk-xxx",
            "livekit": {"api_key": "lk", "api_secret": "lks"},
        }

    @pytest.mark.asyncio
    async def test_invalid_google_key_returns_error_without_writing(
        self, organization_service, mock_supabase_client
    ):
        org_id = uuid4()

        organization_service.validate_google_api_key = AsyncMock(
            return_value=(False, "key rejected")
        )

        with patch("src.organization.service.encrypt_data") as mock_enc:
            result, error = await organization_service.update_organization(
                org_id, OrganizationUpdate(google_api_key="BAD_KEY")
            )

        assert result is None
        assert "Invalid Google API key" in error
        mock_enc.assert_not_called()
        # No update call was issued.
        mock_supabase_client.table.return_value.update.assert_not_called()


class TestOrgProviderCredentialsRead:
    """_organization_from_dict resolves the Google key from the blob."""

    def test_reads_google_key_from_decrypted_blob(self):
        with patch("src.organization.service.decrypt_data") as mock_dec:
            mock_dec.return_value = {"google": "GEM_FROM_BLOB"}
            org = OrganizationService._organization_from_dict(
                _row(uuid4(), provider_credentials="ENC_BLOB", google_api_key=None)
            )
        assert org.google_api_key == "GEM_FROM_BLOB"
        assert org.provider_credentials == "ENC_BLOB"

    def test_falls_back_to_plaintext_column_when_no_blob(self):
        """Un-migrated rows still surface the legacy plaintext google_api_key."""
        with patch("src.organization.service.decrypt_data") as mock_dec:
            org = OrganizationService._organization_from_dict(
                _row(uuid4(), provider_credentials=None, google_api_key="PLAINTEXT_KEY")
            )
        assert org.google_api_key == "PLAINTEXT_KEY"
        # No blob to decrypt.
        mock_dec.assert_not_called()

    def test_decrypt_failure_falls_back_to_plaintext_column(self):
        with patch("src.organization.service.decrypt_data") as mock_dec:
            mock_dec.side_effect = Exception("bad key")
            org = OrganizationService._organization_from_dict(
                _row(
                    uuid4(),
                    provider_credentials="CORRUPT_BLOB",
                    google_api_key="PLAINTEXT_KEY",
                )
            )
        # Decrypt failed → fall back to the plaintext column (graceful).
        assert org.google_api_key == "PLAINTEXT_KEY"

    def test_blob_without_google_leaves_key_none(self):
        with patch("src.organization.service.decrypt_data") as mock_dec:
            mock_dec.return_value = {"openai": "sk-xxx"}  # no google entry
            org = OrganizationService._organization_from_dict(
                _row(uuid4(), provider_credentials="ENC_BLOB", google_api_key=None)
            )
        assert org.google_api_key is None


class TestMergeProviderCredentials:
    """Unit tests for the _merge_provider_credentials helper."""

    def test_merge_preserves_existing_providers(self):
        with patch("src.organization.service.decrypt_data") as mock_dec, patch(
            "src.organization.service.encrypt_data"
        ) as mock_enc:
            mock_dec.return_value = {"google": "G1", "openai": "O1"}
            mock_enc.return_value = "ENC"
            blob = OrganizationService._merge_provider_credentials(
                "OLD_BLOB", {"deepgram": "D1"}
            )
        mock_enc.assert_called_once_with(
            {"google": "G1", "openai": "O1", "deepgram": "D1"}
        )
        assert blob == "ENC"

    def test_merge_none_value_clears_provider(self):
        with patch("src.organization.service.decrypt_data") as mock_dec, patch(
            "src.organization.service.encrypt_data"
        ) as mock_enc:
            mock_dec.return_value = {"google": "G1", "openai": "O1"}
            mock_enc.return_value = "ENC"
            OrganizationService._merge_provider_credentials(
                "OLD_BLOB", {"openai": None}
            )
        mock_enc.assert_called_once_with({"google": "G1"})

    def test_merge_returns_none_when_all_providers_cleared(self):
        with patch("src.organization.service.decrypt_data") as mock_dec, patch(
            "src.organization.service.encrypt_data"
        ) as mock_enc:
            mock_dec.return_value = {"google": "G1"}
            blob = OrganizationService._merge_provider_credentials(
                "OLD_BLOB", {"google": None}
            )
        mock_enc.assert_not_called()
        assert blob is None

    def test_merge_with_no_existing_blob(self):
        with patch("src.organization.service.encrypt_data") as mock_enc:
            mock_enc.return_value = "ENC"
            OrganizationService._merge_provider_credentials(
                None, {"google": "G1", "openai": "O1"}
            )
        mock_enc.assert_called_once_with({"google": "G1", "openai": "O1"})

    def test_merge_decrypt_failure_starts_from_empty(self):
        with patch("src.organization.service.decrypt_data") as mock_dec, patch(
            "src.organization.service.encrypt_data"
        ) as mock_enc:
            mock_dec.side_effect = Exception("bad key")
            mock_enc.return_value = "ENC"
            OrganizationService._merge_provider_credentials(
                "CORRUPT_BLOB", {"google": "G1"}
            )
        # Existing blob undecryptable → start fresh, only the new key remains.
        mock_enc.assert_called_once_with({"google": "G1"})
