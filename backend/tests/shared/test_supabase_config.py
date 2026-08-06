"""Tests for Supabase client isolation between auth and service-role DB access."""

from unittest.mock import MagicMock, patch

from shared.config.supabase import SupabaseConfig, create_isolated_supabase_client
from shared.organization.service import BaseOrganizationService


class TestSupabaseConfig:
    """Ensure auth pollution cannot affect service-role database writes."""

    def test_service_client_is_separate_from_shared_client(self) -> None:
        auth_client = MagicMock(name="auth_client")
        service_client = MagicMock(name="service_client")

        config = SupabaseConfig()
        with patch.object(
            config,
            "_build_client",
            side_effect=[auth_client, service_client],
        ):
            assert config.client is auth_client
            assert config.service_client is service_client
            assert config.client is not config.service_client

    def test_base_organization_service_uses_service_client(self) -> None:
        mock_service_client = MagicMock(name="service_client")

        with patch("shared.organization.service.supabase_config") as mock_config:
            mock_config.is_configured.return_value = True
            mock_config.service_client = mock_service_client
            org_service = BaseOrganizationService()

        assert org_service.supabase is mock_service_client

    def test_create_isolated_supabase_client_builds_fresh_client(self) -> None:
        isolated_client = MagicMock(name="isolated_client")

        with patch(
            "shared.config.supabase.create_client",
            return_value=isolated_client,
        ) as create_client_mock, patch(
            "shared.config.supabase.settings.supabase_url",
            "http://127.0.0.1:54321",
        ), patch(
            "shared.config.supabase.settings.supabase_service_key",
            "service-key",
        ):
            assert create_isolated_supabase_client() is isolated_client
            create_client_mock.assert_called_once_with(
                "http://127.0.0.1:54321",
                "service-key",
            )
