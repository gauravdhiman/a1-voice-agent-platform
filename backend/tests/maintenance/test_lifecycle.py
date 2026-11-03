"""Ensure external mode never starts duplicate API maintenance loops."""

from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import main
import pytest


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["in_process", "external"])
async def test_api_lifecycle_obeys_maintenance_mode(mode):
    targets = [
        "src.services.token_refresh_service.start_token_refresh_service",
        "src.billing.plan_migration_scheduler.start_plan_migration_scheduler",
        "src.billing.free_plan_renewal_scheduler.start_free_plan_renewal_scheduler",
        "src.phone_numbers.rental_scheduler.start_phone_number_rental_scheduler",
        "src.notifications.retry_scheduler.start_notification_retry_scheduler",
        "src.services.token_refresh_service.stop_token_refresh_service",
        "src.billing.plan_migration_scheduler.stop_plan_migration_scheduler",
        "src.billing.free_plan_renewal_scheduler.stop_free_plan_renewal_scheduler",
        "src.phone_numbers.rental_scheduler.stop_phone_number_rental_scheduler",
        "src.notifications.retry_scheduler.stop_notification_retry_scheduler",
    ]
    with ExitStack() as stack:
        callbacks = [
            stack.enter_context(patch(target, new=AsyncMock())) for target in targets
        ]
        stack.enter_context(
            patch.object(
                main,
                "settings",
                SimpleNamespace(
                    jwt_secret_key="local-test",
                    environment="test",
                    maintenance_mode=mode,
                ),
            )
        )
        for name in (
            "setup_manual_opentelemetry",
            "emit_log",
            "emit_metric",
            "shutdown_opentelemetry",
        ):
            stack.enter_context(patch.object(main, name))
        stack.enter_context(
            patch("shared.voice_agents.tool_service.ToolService", new=MagicMock())
        )
        stack.enter_context(
            patch(
                "shared.voice_agents.tools.base.platform_tool_registry."
                "platform_tool_registry.register_tools_from_package"
            )
        )
        async with main.lifespan(MagicMock()):
            pass
    for callback in callbacks:
        assert callback.await_count == (1 if mode == "in_process" else 0)
