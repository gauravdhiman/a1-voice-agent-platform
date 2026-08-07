"""Tests for organization provisioning on first-time signup."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

from src.organization.models import OrganizationCreate
from src.organization.provisioning import ensure_default_organization_for_user

USER_ID = UUID("12345678-1234-5678-1234-567812345678")
ORG_ID = UUID("87654321-4321-8765-cba9-876543210987")
ROLE_ID = UUID("11111111-2222-3333-4444-555555555555")


@pytest.fixture
def mock_organization() -> MagicMock:
    organization = MagicMock()
    organization.id = ORG_ID
    return organization


class TestEnsureDefaultOrganizationForUser:
    """Ensure first-time users receive a normal organization (not a 'dummy' org)."""

    @pytest.mark.asyncio
    async def test_skips_when_user_already_has_organization(
        self, mock_organization: MagicMock
    ) -> None:
        with patch(
            "src.organization.provisioning._user_has_organization",
            return_value=True,
        ):
            org_id, error = await ensure_default_organization_for_user(
                USER_ID,
                "member@example.com",
            )

        assert org_id is None
        assert error is None

    @pytest.mark.asyncio
    async def test_creates_organization_with_name_based_slug(
        self, mock_organization: MagicMock
    ) -> None:
        """Provisioned orgs use a slug derived from the org name, not *-dummy-org."""
        mock_role = MagicMock()
        mock_role.id = ROLE_ID
        create_mock = AsyncMock(return_value=(mock_organization, None))

        with patch(
            "src.organization.provisioning._user_has_organization",
            return_value=False,
        ), patch(
            "src.organization.provisioning.role_service.get_role_by_name",
            new=AsyncMock(return_value=(mock_role, None)),
        ), patch(
            "src.organization.provisioning.organization_service.create_organization",
            new=create_mock,
        ), patch(
            "src.organization.provisioning._is_slug_taken",
            return_value=False,
        ), patch(
            "src.organization.provisioning.user_role_service.assign_role_to_user",
            new=AsyncMock(return_value=(MagicMock(), None)),
        ):
            org_id, error = await ensure_default_organization_for_user(
                USER_ID,
                "member@example.com",
                organization_name="Ada Org",
            )

        assert error is None
        assert org_id == ORG_ID
        create_mock.assert_awaited_once()
        org_data: OrganizationCreate = create_mock.await_args.args[0]
        assert org_data.name == "Ada Org"
        assert org_data.slug == "ada-org"
        assert "dummy" not in org_data.slug
        assert "default" not in org_data.slug.lower()
        assert org_data.description is None or "Default organization" not in (
            org_data.description or ""
        )

    @pytest.mark.asyncio
    async def test_slug_collision_appends_unique_suffix(
        self, mock_organization: MagicMock
    ) -> None:
        mock_role = MagicMock()
        mock_role.id = ROLE_ID
        create_mock = AsyncMock(return_value=(mock_organization, None))

        with patch(
            "src.organization.provisioning._user_has_organization",
            return_value=False,
        ), patch(
            "src.organization.provisioning.role_service.get_role_by_name",
            new=AsyncMock(return_value=(mock_role, None)),
        ), patch(
            "src.organization.provisioning.organization_service.create_organization",
            new=create_mock,
        ), patch(
            "src.organization.provisioning._is_slug_taken",
            side_effect=[True, False],
        ), patch(
            "src.organization.provisioning.user_role_service.assign_role_to_user",
            new=AsyncMock(return_value=(MagicMock(), None)),
        ):
            org_id, error = await ensure_default_organization_for_user(
                USER_ID,
                "member@example.com",
                organization_name="Ada Org",
            )

        assert error is None
        assert org_id == ORG_ID
        org_data: OrganizationCreate = create_mock.await_args.args[0]
        assert org_data.slug.startswith("ada-org-")
        assert "dummy" not in org_data.slug
