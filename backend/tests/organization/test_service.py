"""
Organization Service Tests
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from src.organization.models import Organization, OrganizationCreate, OrganizationUpdate


@pytest.fixture
def organization_service(mock_supabase_client):
    """Create OrganizationService instance."""
    with patch("shared.organization.service.supabase_config") as mock_config:
        mock_config.client = mock_supabase_client
        mock_config.service_client = mock_supabase_client
        from src.organization.service import OrganizationService

        return OrganizationService()


@pytest.fixture
def sample_org_id():
    """Sample organization ID."""
    return uuid4()


@pytest.fixture
def sample_organization(sample_org_id):
    """Sample organization data."""
    now = datetime.now(timezone.utc)
    return {
        "id": str(sample_org_id),
        "name": "Test Org",
        "description": "A test organization",
        "slug": "test-org",
        "website": "https://test.org",
        "is_active": True,
        "industry": "Tech",
        "location": "Global",
        "business_details": None,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }


@pytest.fixture
def sample_organization_create():
    """Sample organization create data."""
    return OrganizationCreate(
        name="New Org",
        description="A new test organization",
        slug="new-org",
        website="https://new.org",
    )


class TestOrganizationService:
    """Test cases for organization service."""

    @pytest.mark.asyncio
    async def test_process_invitation_claims_rpc_with_normalized_email(
        self, organization_service, mock_supabase_client
    ):
        """Invitation claims are delegated to the atomic database function."""
        invitation_id = uuid4()
        organization_id = uuid4()
        invited_by = uuid4()
        response = MagicMock()
        response.data = {
            "success": True,
            "invitation": {
                "id": str(invitation_id),
                "email": "Invitee@Example.com",
                "organization_id": str(organization_id),
                "invited_by": str(invited_by),
                "token": "invite-token",
                "status": "accepted",
                "expires_at": "2099-01-01T00:00:00+00:00",
                "created_at": "2026-01-01T00:00:00+00:00",
                "accepted_at": "2026-01-01T00:00:00+00:00",
                "organization_name": "Acme Plumbing",
            },
        }
        mock_supabase_client.rpc.return_value.execute.return_value = response

        invitation, error = await organization_service.process_invitation(
            "invite-token",
            UUID("12345678-1234-5678-1234-567812345678"),
            "  INVITEE@example.com ",
        )

        assert error is None
        assert invitation is not None
        assert invitation.organization_id == organization_id
        mock_supabase_client.rpc.assert_called_once_with(
            "claim_invitation",
            {
                "p_token": "invite-token",
                "p_user_id": "12345678-1234-5678-1234-567812345678",
                "p_email": "invitee@example.com",
            },
        )

    @pytest.mark.asyncio
    async def test_process_invitation_maps_claim_error_without_exposing_rpc_details(
        self, organization_service, mock_supabase_client
    ):
        """Known claim failures return safe, actionable messages."""
        response = MagicMock()
        response.data = {
            "success": False,
            "error": "invitation_email_mismatch",
        }
        mock_supabase_client.rpc.return_value.execute.return_value = response

        invitation, error = await organization_service.process_invitation(
            "invite-token", uuid4(), "invitee@example.com"
        )

        assert invitation is None
        assert error == "This invitation belongs to a different email address"

    @pytest.mark.asyncio
    async def test_create_organization_success(
        self,
        organization_service,
        mock_supabase_client,
        sample_organization_create,
        sample_org_id,
    ):
        """Create organization successfully."""
        now = datetime.now(timezone.utc)

        mock_response = MagicMock()
        mock_response.data = [
            {
                "id": str(sample_org_id),
                "name": sample_organization_create.name,
                "description": sample_organization_create.description,
                "slug": sample_organization_create.slug,
                "website": str(sample_organization_create.website),
                "is_active": True,
                "industry": None,
                "location": None,
                "business_details": None,
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
            }
        ]
        mock_supabase_client.table.return_value.insert.return_value.execute.return_value = (
            mock_response
        )

        result, error = await organization_service.create_organization(
            sample_organization_create
        )

        assert error is None
        assert result is not None
        assert result.name == "New Org"
        assert result.slug == "new-org"

    @pytest.mark.asyncio
    async def test_create_organization_minimal(
        self,
        organization_service,
        mock_supabase_client,
        sample_org_id,
    ):
        """Create organization with minimal data."""
        now = datetime.now(timezone.utc)
        org_data = OrganizationCreate(
            name="Minimal Org",
            slug="minimal",
        )

        mock_response = MagicMock()
        mock_response.data = [
            {
                "id": str(sample_org_id),
                "name": org_data.name,
                "description": None,
                "slug": org_data.slug,
                "website": None,
                "is_active": True,
                "industry": None,
                "location": None,
                "business_details": None,
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
            }
        ]
        mock_supabase_client.table.return_value.insert.return_value.execute.return_value = (
            mock_response
        )

        result, error = await organization_service.create_organization(org_data)

        assert error is None
        assert result is not None
        assert result.name == "Minimal Org"
        assert result.description is None
        assert result.website is None

    @pytest.mark.asyncio
    async def test_create_organization_failure(
        self,
        organization_service,
        mock_supabase_client,
        sample_organization_create,
    ):
        """Handle organization creation failure."""
        mock_response = MagicMock()
        mock_response.data = None
        mock_supabase_client.table.return_value.insert.return_value.execute.return_value = (
            mock_response
        )

        result, error = await organization_service.create_organization(
            sample_organization_create
        )

        assert result is None
        assert error == "Failed to create organization"

    @pytest.mark.asyncio
    async def test_get_organization_success(
        self,
        organization_service,
        mock_supabase_client,
        sample_organization,
        sample_org_id,
    ):
        """Get organization by ID."""
        mock_response = MagicMock()
        mock_response.data = [sample_organization]
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = (
            mock_response
        )

        result, error = await organization_service.get_organization_by_id(sample_org_id)

        assert error is None
        assert result is not None
        assert result.id == sample_org_id
        assert result.name == "Test Org"

    @pytest.mark.asyncio
    async def test_get_organization_not_found(
        self,
        organization_service,
        mock_supabase_client,
        sample_org_id,
    ):
        """Organization not found."""
        mock_response = MagicMock()
        mock_response.data = []
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = (
            mock_response
        )

        result, error = await organization_service.get_organization_by_id(sample_org_id)

        assert result is None
        assert error == "Organization not found"

    @pytest.mark.asyncio
    async def test_update_organization_success(
        self,
        organization_service,
        mock_supabase_client,
        sample_org_id,
    ):
        """Update organization successfully."""
        now = datetime.now(timezone.utc)
        updated_org = {
            "id": str(sample_org_id),
            "name": "Updated Org",
            "description": "Updated description",
            "slug": "updated-org",
            "website": "https://updated.org",
            "is_active": True,
            "industry": None,
            "location": None,
            "business_details": None,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }

        mock_response = MagicMock()
        mock_response.data = [updated_org]
        mock_supabase_client.table.return_value.update.return_value.eq.return_value.execute.return_value = (
            mock_response
        )

        org_update = OrganizationUpdate(
            name="Updated Org",
            description="Updated description",
        )

        result, error = await organization_service.update_organization(
            sample_org_id, org_update
        )

        assert error is None
        assert result is not None
        assert result.name == "Updated Org"
        assert result.description == "Updated description"

    @pytest.mark.asyncio
    async def test_update_organization_partial(
        self,
        organization_service,
        mock_supabase_client,
        sample_org_id,
        sample_organization,
    ):
        """Partial update preserves other fields."""
        now = datetime.now(timezone.utc)
        updated_org = {
            **sample_organization,
            "name": "Partial Updated Org",
            "updated_at": now.isoformat(),
        }

        mock_response = MagicMock()
        mock_response.data = [updated_org]
        mock_supabase_client.table.return_value.update.return_value.eq.return_value.execute.return_value = (
            mock_response
        )

        org_update = OrganizationUpdate(name="Partial Updated Org")

        result, error = await organization_service.update_organization(
            sample_org_id, org_update
        )

        assert error is None
        assert result is not None
        assert result.name == "Partial Updated Org"
        assert result.description == "A test organization"  # Unchanged

    @pytest.mark.asyncio
    async def test_update_organization_rejects_invalid_timezone(
        self, organization_service, sample_org_id
    ):
        """Timezone updates must be valid IANA names."""
        result, error = await organization_service.update_organization(
            sample_org_id, OrganizationUpdate(timezone="Not/A_Real_Zone")
        )

        assert result is None
        assert error is not None
        assert "invalid" in error.lower()

    @pytest.mark.asyncio
    async def test_update_organization_clears_timezone_with_blank_string(
        self,
        organization_service,
        mock_supabase_client,
        sample_org_id,
        sample_organization,
    ):
        """Empty timezone clears the org default."""
        now = datetime.now(timezone.utc)
        updated_org = {
            **sample_organization,
            "timezone": None,
            "updated_at": now.isoformat(),
        }

        mock_response = MagicMock()
        mock_response.data = [updated_org]
        mock_supabase_client.table.return_value.update.return_value.eq.return_value.execute.return_value = (
            mock_response
        )

        result, error = await organization_service.update_organization(
            sample_org_id, OrganizationUpdate(timezone="")
        )

        assert error is None
        assert result is not None
        update_payload = mock_supabase_client.table.return_value.update.call_args[0][0]
        assert update_payload["timezone"] is None

    @pytest.mark.asyncio
    async def test_update_organization_rejects_invalid_slug(
        self, organization_service, sample_org_id
    ):
        """Slug updates must pass format validation."""
        result, error = await organization_service.update_organization(
            sample_org_id, OrganizationUpdate(slug="api")
        )

        assert result is None
        assert error is not None
        assert "reserved" in error.lower()

    @pytest.mark.asyncio
    async def test_update_organization_rejects_taken_slug(
        self, organization_service, mock_supabase_client, sample_org_id
    ):
        """Slug updates must be unique across organizations."""
        taken_response = MagicMock()
        taken_response.data = [{"id": str(uuid4())}]
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.neq.return_value.limit.return_value.execute.return_value = (
            taken_response
        )

        result, error = await organization_service.update_organization(
            sample_org_id, OrganizationUpdate(slug="acme")
        )

        assert result is None
        assert error == "Slug 'acme' is already taken"

    @pytest.mark.asyncio
    async def test_delete_organization_success(
        self,
        organization_service,
        mock_supabase_client,
        sample_org_id,
    ):
        """Delete organization successfully."""
        mock_response = MagicMock()
        mock_response.data = [{"id": str(sample_org_id)}]
        mock_supabase_client.table.return_value.delete.return_value.eq.return_value.execute.return_value = (
            mock_response
        )

        result, error = await organization_service.delete_organization(sample_org_id)

        assert error is None
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_organization_not_found(
        self,
        organization_service,
        mock_supabase_client,
        sample_org_id,
    ):
        """Organization not found for deletion."""
        mock_response = MagicMock()
        mock_response.data = []
        mock_supabase_client.table.return_value.delete.return_value.eq.return_value.execute.return_value = (
            mock_response
        )

        result, error = await organization_service.delete_organization(sample_org_id)

        assert result is False
        assert error == "Organization not found"

    @pytest.mark.asyncio
    async def test_list_organizations_success(
        self,
        organization_service,
        mock_supabase_client,
        sample_organization,
    ):
        """List organizations successfully."""
        mock_response = MagicMock()
        mock_response.data = [sample_organization]
        mock_supabase_client.table.return_value.select.return_value.execute.return_value = (
            mock_response
        )

        results, error = await organization_service.get_all_organizations()

        assert error is None
        assert len(results) == 1
        assert results[0].name == "Test Org"

    @pytest.mark.asyncio
    async def test_list_organizations_empty(
        self,
        organization_service,
        mock_supabase_client,
    ):
        """List organizations when empty."""
        mock_response = MagicMock()
        mock_response.data = []
        mock_supabase_client.table.return_value.select.return_value.execute.return_value = (
            mock_response
        )

        results, error = await organization_service.get_all_organizations()

        assert error is None
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_complete_onboarding_success(
        self,
        organization_service,
        mock_supabase_client,
        sample_org_id,
        sample_organization,
    ):
        """Complete onboarding sets onboarding_completed to True."""
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        completed_org = {
            **sample_organization,
            "onboarding_completed": True,
            "updated_at": now.isoformat(),
        }

        mock_response = MagicMock()
        mock_response.data = [completed_org]
        mock_supabase_client.table.return_value.update.return_value.eq.return_value.execute.return_value = (
            mock_response
        )

        result, error = await organization_service.complete_onboarding(sample_org_id)

        assert error is None
        assert result is not None
        assert result.onboarding_completed is True
        # Verify the update call used onboarding_completed=True
        mock_supabase_client.table.return_value.update.assert_called_once_with(
            {"onboarding_completed": True}
        )

    @pytest.mark.asyncio
    async def test_complete_onboarding_not_found(
        self,
        organization_service,
        mock_supabase_client,
        sample_org_id,
    ):
        """Complete onboarding returns error when org not found."""
        mock_response = MagicMock()
        mock_response.data = []
        mock_supabase_client.table.return_value.update.return_value.eq.return_value.execute.return_value = (
            mock_response
        )

        result, error = await organization_service.complete_onboarding(sample_org_id)

        assert result is None
        assert error == "Organization not found"

    def test_organization_update_no_onboarding_completed_field(self):
        """OrganizationUpdate must not allow setting onboarding_completed."""
        from shared.organization.models import OrganizationUpdate
        import pydantic

        # onboarding_completed should not be a field on OrganizationUpdate
        assert "onboarding_completed" not in OrganizationUpdate.model_fields
