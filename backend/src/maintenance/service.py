"""Composition root for the independently deployed maintenance service."""

import asyncio
from contextlib import asynccontextmanager

from shared.config.opentelemetry import (
    setup_manual_opentelemetry,
    shutdown_opentelemetry,
)
from shared.voice_agents.tool_service import ToolService
from shared.voice_agents.tools.base.platform_tool_registry import platform_tool_registry

from .coordinator import PostgresRunCoordinator
from .heartbeat import Heartbeat
from .http import create_maintenance_app
from .jobs import maintenance_interval_seconds, maintenance_jobs
from .runner import MaintenanceRunner


def create_application(*, client, token: str, environment: str, heartbeat_url=""):
    """Build a worker with explicit credentials and no in-process schedulers."""
    coordinator = PostgresRunCoordinator(client, maintenance_interval_seconds)
    runner = MaintenanceRunner(maintenance_jobs(), coordinator)
    app = create_maintenance_app(
        runner,
        token,
        coordinator.status,
        maintenance_interval_seconds,
        heartbeat=Heartbeat(heartbeat_url).send if heartbeat_url else None,
    )

    @asynccontextmanager
    async def lifespan(_app):
        setup_manual_opentelemetry("247ai-maintenance")
        try:
            platform_tool_registry.register_tools_from_package(
                "shared.voice_agents.tools.implementations"
            )
            if environment != "test":
                _, error = await ToolService().migrate_legacy_oauth_client_secrets()
                if error:
                    raise RuntimeError("Legacy OAuth secret migration failed")
            yield
        finally:
            await asyncio.to_thread(shutdown_opentelemetry)

    app.router.lifespan_context = lifespan
    return app
