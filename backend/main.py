"""
FastAPI application entry point for multi-tenant SaaS platform.
Includes authentication, health endpoints and CORS configuration.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime

import uvicorn
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from opentelemetry import trace
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from src.auth.routes import auth_router
from src.billing.admin_plan_routes import router as admin_plan_router
from src.billing.routes import router as billing_router
from src.call_artifacts import call_artifacts_router
from src.call_logs import call_logs_router
from src.escalations.routes import escalations_router
from src.leads.routes import admin_leads_router, public_leads_router
from src.notifications.routes import router as notification_router
from src.organization.public_routes import public_org_router
from src.organization.routes import organization_router
from src.phone_numbers.routes import router as phone_number_router
from src.rbac.routes import rbac_router
from src.security import (
    CanonicalHostMiddleware,
    EmbedAwareCORSMiddleware,
    SecurityHeadersMiddleware,
    limiter,
    rate_limit_handler,
)
from src.security.validation_errors import sanitize_validation_errors
from src.voice_agents import (
    agent_router,
    demo_public_router,
    embed_router,
    organization_tool_router,
    platform_skill_router,
    preset_router,
    skill_router,
    tool_router,
    voice_router,
)
from src.voice_templates import platform_voice_templates_router, voice_templates_router

from shared.config import settings

# Import OpenTelemetry setup function first to ensure proper logging configuration
from shared.config.opentelemetry import (
    emit_log,
    emit_metric,
    instrument_fastapi,
    logging_level,
    setup_manual_opentelemetry,
    shutdown_opentelemetry,
)
from shared.observability.health import Readiness

# Configure logging to ensure it outputs to stdout with proper formatting
# The OpenTelemetry logging handler is added in the setup_manual_opentelemetry function
logging.basicConfig(
    level=logging_level, format="%(name)s - %(levelname)s - %(message)s"
)

# Set up OpenTelemetry explicitly to ensure logger and meter providers are available
# This needs to happen before configuring logging to ensure proper integration


# Get tracer for this module
tracer = trace.get_tracer(__name__)

logging.info("Backend application starting up")
print("Backend application starting up")  # Print to stdout for visibility


def create_app() -> FastAPI:
    """Create and configure FastAPI application.

    Returns:
        FastAPI: Configured application instance with all routes, middleware,
            and lifecycle management

    Notes:
        - Uses lifespan context manager for startup/shutdown
        - Includes auth, RBAC, organization, billing, notification and voice routers
        - Configures CORS for cross-origin requests
        - Instruments with OpenTelemetry for observability
    """

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Multi-tenant SaaS platform API",
        debug=settings.debug,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        lifespan=lifespan,
    )

    # Attach shared rate limiter and 429 handler
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_handler)

    @app.exception_handler(RequestValidationError)
    async def request_validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Strip potentially secret request bodies from validation errors."""
        return JSONResponse(
            status_code=422,
            content={"detail": sanitize_validation_errors(exc.errors())},
        )

    # Add SlowAPI middleware for rate limiting
    app.add_middleware(SlowAPIMiddleware)

    # Add security headers to all responses
    app.add_middleware(SecurityHeadersMiddleware)

    # Block direct *.run.app Host in production (custom domain only)
    app.add_middleware(CanonicalHostMiddleware)

    # Configure CORS
    app.add_middleware(
        EmbedAwareCORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_credentials,
        allow_methods=settings.cors_methods,
        allow_headers=list(set(settings.cors_headers + ["traceparent"])),
        expose_headers=["x-request-id", "x-trace-id"],
    )

    instrument_fastapi(app)

    # Include authentication routes
    app.include_router(auth_router)

    # Include RBAC routes
    app.include_router(rbac_router)

    # Include organization routes
    app.include_router(organization_router)

    # Include billing routes
    app.include_router(billing_router)
    app.include_router(admin_plan_router)

    # Include notification routes
    app.include_router(notification_router)

    # Include phone number routes
    app.include_router(phone_number_router)

    # Include voice agent and tool routes
    app.include_router(agent_router)
    app.include_router(tool_router)
    app.include_router(organization_tool_router)
    app.include_router(voice_router)

    # Include skill routes (org-level + platform admin)
    app.include_router(skill_router)
    app.include_router(platform_skill_router)

    # Include voice-engine preset routes (platform admin CRUD + published listing)
    app.include_router(preset_router)
    # Include embed routes (public, no auth required)
    app.include_router(embed_router)
    app.include_router(public_org_router)
    app.include_router(demo_public_router)
    app.include_router(public_leads_router)
    app.include_router(admin_leads_router)

    # Include voice templates routes
    app.include_router(voice_templates_router)
    app.include_router(platform_voice_templates_router)

    # Include call logs routes
    app.include_router(call_logs_router)

    # Include callback escalation routes (org-scoped owner workflow)
    app.include_router(escalations_router)

    # Include authenticated recording and artifact routes
    app.include_router(call_artifacts_router)

    return app


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI application.

    Manages startup and shutdown events for background services.
    Ensures proper cleanup of resources when application stops.

    Args:
        app: FastAPI application instance

    Yields:
        None

    Example:
        ```python
        app = FastAPI(lifespan=lifespan)
        # Application starts
        # ... app runs ...
        # Application stops
        ```

    Notes:
        - Starts token refresh service on startup
        - Stops token refresh service on shutdown
        - Ensures graceful shutdown of background tasks
    """
    setup_manual_opentelemetry("247ai-backend")
    # Emit startup telemetry after the SDK providers are installed. Emitting
    # at module import would cache no-op instruments before the provider exists.
    emit_log(
        "Backend application started", "INFO", {"service": "247ai-backend"}
    )
    emit_metric("backend.app.start", 1, {"service": "247ai-backend"})
    # Startup — fail fast if required secrets are not configured
    if not settings.jwt_secret_key:
        raise RuntimeError(
            "JWT_SECRET_KEY is not set. "
            "Set it to your Supabase JWT secret "
            "(Dashboard → Settings → API → JWT Secret)."
        )

    from src.billing.free_plan_renewal_scheduler import (
        start_free_plan_renewal_scheduler,
        stop_free_plan_renewal_scheduler,
    )
    from src.billing.plan_migration_scheduler import (
        start_plan_migration_scheduler,
        stop_plan_migration_scheduler,
    )
    from src.notifications.retry_scheduler import (
        start_notification_retry_scheduler,
        stop_notification_retry_scheduler,
    )
    from src.phone_numbers.rental_scheduler import (
        start_phone_number_rental_scheduler,
        stop_phone_number_rental_scheduler,
    )
    from src.services.token_refresh_service import (
        start_token_refresh_service,
        stop_token_refresh_service,
    )

    from shared.voice_agents.tool_service import ToolService
    from shared.voice_agents.tools.base.platform_tool_registry import (
        platform_tool_registry,
    )

    # Register in-tree platform tools for runtime discovery. Database writes
    # for platform-tool master data happen only through the explicit CLI.
    platform_tool_registry.register_tools_from_package(
        "shared.voice_agents.tools.implementations"
    )

    # Sync with database
    tool_service = ToolService()

    # Master data is intentionally not seeded during application startup.
    # Run ``python -m src.master_data.cli`` for a dry-run preview, then apply
    # the reviewed plan as a separate release/bootstrap operation.

    # Remove any pre-encryption OAuth client secrets before the refresh worker
    # starts. The migration is idempotent and fails closed: continuing while a
    # known credential migration is broken would leave secrets in auth_config.
    # In the isolated E2E stack (ENVIRONMENT=test) the Supabase REST endpoint
    # is a mock (mock-key) so the migration would 401 before it can even read;
    # the E2E database is fresh with no real secrets to migrate, so we skip it
    # there rather than crashing the backend. Production and staging still fail
    # closed — a real secret-store failure must not be silently ignored.
    if settings.environment == "test":
        logging.info(
            "Skipping legacy OAuth client-secret migration in test environment"
        )
    else:
        migrated_client_secrets, migration_error = (
            await tool_service.migrate_legacy_oauth_client_secrets()
        )
        if migration_error:
            raise RuntimeError(migration_error)
        if migrated_client_secrets:
            logging.info(
                "Migrated %s legacy OAuth client-secret row(s) to encrypted storage",
                migrated_client_secrets,
            )

    # Start token refresh service
    logging.info("Starting token refresh service...")
    await start_token_refresh_service(tool_service)
    logging.info("Token refresh service started")

    logging.info("Starting plan migration scheduler...")
    await start_plan_migration_scheduler()
    logging.info("Plan migration scheduler started")

    logging.info("Starting free-plan renewal scheduler...")
    await start_free_plan_renewal_scheduler()
    logging.info("Free-plan renewal scheduler started")

    logging.info("Starting phone-number rental scheduler...")
    await start_phone_number_rental_scheduler()
    logging.info("Phone-number rental scheduler started")

    logging.info("Starting notification retry scheduler...")
    await start_notification_retry_scheduler()
    logging.info("Notification retry scheduler started")

    yield

    # Shutdown
    logging.info("Shutting down plan migration scheduler...")
    await stop_plan_migration_scheduler()
    logging.info("Plan migration scheduler stopped")

    logging.info("Shutting down free-plan renewal scheduler...")
    await stop_free_plan_renewal_scheduler()
    logging.info("Free-plan renewal scheduler stopped")

    logging.info("Shutting down phone-number rental scheduler...")
    await stop_phone_number_rental_scheduler()
    logging.info("Phone-number rental scheduler stopped")

    logging.info("Shutting down notification retry scheduler...")
    await stop_notification_retry_scheduler()
    logging.info("Notification retry scheduler stopped")

    logging.info("Shutting down token refresh service...")
    await stop_token_refresh_service()
    logging.info("Token refresh service stopped")
    await asyncio.to_thread(shutdown_opentelemetry)


# Create FastAPI app instance
app = create_app()


@app.get("/")
async def root():
    """Root endpoint with basic API information."""
    # Log a message using OpenTelemetry
    logging.info("Root endpoint accessed")
    print("Root endpoint accessed")  # Print to stdout for visibility
    emit_metric("backend.endpoint.access", 1, {"endpoint": "/"})

    return JSONResponse(
        {
            "message": f"{settings.app_name} API",
            "version": settings.app_version,
            "environment": settings.environment,
            "timestamp": datetime.utcnow().isoformat(),
        }
    )


readiness = Readiness(settings)


@app.get("/health")
async def health_check():
    """Dependency-aware health for load balancers; 503 when Supabase is unavailable."""
    return await readiness.response()


@app.get("/health/ready")
async def readiness_check():
    """Bounded, cached readiness without sensitive dependency diagnostics."""
    return await readiness.response()


@app.get("/health/live")
async def liveness_check():
    """Liveness check for Kubernetes deployments."""
    # Log a message using OpenTelemetry
    logging.info("Liveness check endpoint accessed")
    emit_metric("backend.liveness.check", 1, {"status": "alive"})

    return JSONResponse(
        {
            "status": "alive",
            "timestamp": datetime.utcnow().isoformat(),
        }
    )


if __name__ == "__main__":
    # For development - use uvicorn CLI for production
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level="debug" if settings.debug else "info",
    )
