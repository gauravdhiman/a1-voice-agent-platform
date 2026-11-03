"""ASGI entry point for the independently deployed maintenance service."""

from src.maintenance.service import create_application

from shared.config import settings, supabase_config

app = create_application(
    client=supabase_config.service_client,
    token=(
        settings.maintenance_auth_token.get_secret_value()
        if settings.maintenance_auth_token
        else ""
    ),
    environment=settings.environment,
    heartbeat_url=(
        settings.maintenance_heartbeat_url.get_secret_value()
        if settings.maintenance_heartbeat_url
        else ""
    ),
)
