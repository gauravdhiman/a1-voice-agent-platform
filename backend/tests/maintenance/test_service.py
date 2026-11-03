"""The worker must fail closed and never start API scheduler loops."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from src.maintenance.service import create_application


def test_service_rejects_missing_database_client_and_token():
    with pytest.raises(ValueError):
        create_application(client=None, token="x" * 32, environment="test")
    with pytest.raises(ValueError):
        create_application(client=MagicMock(), token="", environment="test")


@pytest.mark.asyncio
async def test_worker_fails_closed_when_secret_migration_fails():
    worker = create_application(
        client=MagicMock(), token="x" * 32, environment="production"
    )
    with (
        patch("src.maintenance.service.setup_manual_opentelemetry"),
        patch("src.maintenance.service.shutdown_opentelemetry"),
        patch(
            "src.maintenance.service.platform_tool_registry.register_tools_from_package"
        ),
        patch("src.maintenance.service.ToolService") as service,
    ):
        service.return_value.migrate_legacy_oauth_client_secrets = AsyncMock(
            return_value=(0, "secret detail")
        )
        with pytest.raises(RuntimeError) as error:
            async with worker.router.lifespan_context(worker):
                pass
    assert "secret detail" not in str(error.value)
