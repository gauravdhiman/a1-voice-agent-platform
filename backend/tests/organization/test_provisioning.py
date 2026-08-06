"""Tests for default organization provisioning."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

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
    """Ensure first-time users receive a default tenant."""

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
    async def test_creates_organization_and_assigns_org_admin(
        self, mock_organization: MagicMock
    ) -> None:
        mock_role = MagicMock()
        mock_role.id = ROLE_ID

        with patch(
            "src.organization.provisioning._user_has_organization",
            return_value=False,
        ), patch(
            "src.organization.provisioning.role_service.get_role_by_name",
            new=AsyncMock(return_value=(mock_role, None)),
        ), patch(
            "src.organization.provisioning.organization_service.create_organization",
            new=AsyncMock(return_value=(mock_organization, None)),
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
