"""
Application settings and configuration management.
Uses Pydantic Settings for type-safe configuration handling.
"""

import json
import os
from pathlib import Path
from typing import Annotated, Any, Literal, Optional

from pydantic import AliasChoices, Field, SecretStr, validator
from pydantic_settings import BaseSettings, NoDecode

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def resolve_env_file() -> str:
    """Resolve the environment file used by non-containerized application code.

    ``ENV_FILE`` may contain an absolute path or a path relative to the project
    root. When it is not provided, local development uses ``.env.local``. Docker
    Compose injects the selected file's variables directly, so this fallback is
    primarily for direct backend, worker, and Alembic commands.

    Returns:
        Absolute path to the selected environment file.
    """
    configured = os.getenv("ENV_FILE")
    if configured:
        path = Path(configured)
        return str(path if path.is_absolute() else PROJECT_ROOT / path)
    return str(PROJECT_ROOT / ".env.local")


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    def __init__(self, **values: Any) -> None:
        """Initialize settings using the selected environment file.

        Args:
            **values: Explicit Pydantic setting overrides. The private
                ``_env_file`` override is populated from ``ENV_FILE`` unless a
                caller supplies it explicitly.
        """
        values.setdefault("_env_file", resolve_env_file())
        super().__init__(**values)

    # Application Settings
    app_name: str = Field(default="24x7 AI", description="Application name")
    app_base_url: str = Field(
        default="http://localhost:3000", description="Base URL for the application"
    )
    api_base_url: str = Field(
        default="http://localhost:8000",
        description="Public backend API base URL used for OAuth callbacks",
        validation_alias=AliasChoices("API_BASE_URL", "NEXT_PUBLIC_API_URL"),
    )
    app_version: str = Field(default="1.0.0", description="Application version")
    debug: bool = Field(default=False, description="Debug mode")
    environment: str = Field(
        default="production", description="Environment (development/production/test)"
    )
    maintenance_mode: Literal["in_process", "external"] = Field(
        default="in_process",
        description="Run maintenance loops in the API or in an external worker",
    )
    maintenance_auth_token: Optional[SecretStr] = Field(
        default=None, description="Secret for the separate maintenance service"
    )
    maintenance_heartbeat_url: Optional[SecretStr] = Field(
        default=None, description="Private HTTPS dead-man monitoring URL"
    )

    # Server Settings
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    reload: bool = Field(default=True, description="Auto-reload on code changes")

    # CORS Settings
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
        description="Allowed CORS origins",
    )
    cors_credentials: bool = Field(default=True, description="Allow CORS credentials")
    cors_methods: list[str] = Field(default=["*"], description="Allowed CORS methods")
    cors_headers: list[str] = Field(default=["*"], description="Allowed CORS headers")

    # Database Settings (Future Supabase integration)
    database_url: Optional[str] = Field(
        default=None, description="Database connection URL"
    )

    # Redis Settings (Future integration)
    redis_url: Optional[str] = Field(default=None, description="Redis connection URL")

    # JWT Settings (Future auth integration)
    jwt_secret_key: Optional[str] = Field(default=None, description="JWT secret key")
    # jwt_algorithm is intentionally omitted: middleware.py verifies with HS256.
    jwt_expire_minutes: int = Field(default=30, description="JWT expiration in minutes")

    # External API Settings (Future integrations)
    supabase_url: Optional[str] = Field(
        default=None, description="Supabase project URL"
    )
    supabase_service_key: Optional[str] = Field(
        default=None, description="Supabase service key"
    )
    supabase_anon_key: Optional[str] = Field(
        default=None, description="Supabase anonymous key"
    )
    tinyfish_api_key: Optional[str] = Field(
        default=None, description="TinyFish Fetch API key for website context drafts"
    )
    gemini_api_key: Optional[str] = Field(
        default=None,
        description="Gemini API key used to prepare website context drafts",
    )

    # LinkedIn direct OAuth settings (backend broker; no Supabase custom provider)
    linkedin_client_id: Optional[str] = Field(
        default=None,
        description="LinkedIn OAuth client ID",
        validation_alias=AliasChoices(
            "LINKEDIN_CLIENT_ID",
            "SUPABASE_AUTH_EXTERNAL_LINKEDIN_OIDC_CLIENT_ID",
        ),
    )
    linkedin_client_secret: Optional[str] = Field(
        default=None,
        description="LinkedIn OAuth client secret",
        validation_alias=AliasChoices(
            "LINKEDIN_CLIENT_SECRET",
            "SUPABASE_AUTH_EXTERNAL_LINKEDIN_OIDC_CLIENT_SECRET",
        ),
    )
    linkedin_oauth_scopes: str = Field(
        default="openid profile email",
        description="Space-separated LinkedIn OpenID Connect scopes",
    )

    # Google OAuth settings (backend redirect broker for sign-in)
    google_client_id: Optional[str] = Field(
        default=None,
        description="Google OAuth client ID for backend redirect sign-in",
        validation_alias=AliasChoices(
            "GOOGLE_CLIENT_ID",
            "SUPABASE_AUTH_EXTERNAL_GOOGLE_CLIENT_ID",
            "NEXT_PUBLIC_GOOGLE_CLIENT_ID",
        ),
    )
    google_client_secret: Optional[str] = Field(
        default=None,
        description="Google OAuth client secret for backend redirect sign-in",
        validation_alias=AliasChoices(
            "GOOGLE_CLIENT_SECRET",
            "SUPABASE_AUTH_EXTERNAL_GOOGLE_CLIENT_SECRET",
        ),
    )

    # Stripe Settings
    stripe_secret_key: Optional[str] = Field(
        default=None, description="Stripe secret key"
    )
    stripe_webhook_secret: Optional[str] = Field(
        default=None, description="Stripe webhook endpoint secret"
    )

    # Controlled-SaaS signup gate (Epic A: gated entry + interest funnel).
    # When False, email signup and OAuth sign-in only succeed for invitation
    # holders and allowlisted platform admins; everyone else is directed to
    # the interest form. Flip to True to reopen open SaaS self-serve.
    public_signup_enabled: bool = Field(
        default=False,
        description="Allow open public signup without invitation or allowlist",
    )
    platform_admin_allowlist: Annotated[list[str], NoDecode] = Field(
        default_factory=list,
        description="Comma-separated emails always allowed through the signup gate",
    )

    # Bot protection (Cloudflare Turnstile). Empty secret disables
    # verification (local/dev); production must set both this and the
    # frontend NEXT_PUBLIC_TURNSTILE_SITE_KEY.
    turnstile_secret_key: Optional[str] = Field(
        default=None, description="Cloudflare Turnstile secret key"
    )

    # Resend Settings
    email_provider: str = Field(
        default="resend", description="Configured notification email provider"
    )
    resend_api_key: Optional[str] = Field(
        default=None, description="Resend API key for email notifications"
    )
    resend_from_email: str = Field(
        default="noreply@example.com", description="Default sender email address"
    )
    resend_from_name: str = Field(default="24x7 AI", description="Default sender name")
    email_verification_required: Optional[bool] = Field(
        default=None,
        description=(
            "Verification policy; defaults on in production, sender-based locally"
        ),
    )
    # Phone-number rental billing
    phone_number_billing_check_interval_hours: float = Field(
        default=24,
        gt=0,
        description="How often due phone-number rentals are checked",
    )
    phone_number_billing_grace_period_days: int = Field(
        default=7,
        ge=1,
        description="Days to keep incoming calls disabled before unpaid rental release",
    )
    phone_number_release_retry_interval_hours: float = Field(
        default=24,
        gt=0,
        description="How often provider release-pending numbers are retried",
    )
    notification_retry_check_interval_hours: float = Field(
        default=1,
        gt=0,
        description="How often failed email notifications are retried",
    )
    notification_retry_check_interval_minutes: float = Field(
        default=5,
        gt=0,
        description=(
            "How often notification logs and low-credit outbox rows are processed"
        ),
    )

    # OpenTelemetry Settings
    otel_enabled: bool = Field(default=False, description="Enable OpenTelemetry")
    otel_service_name: str = Field(
        default="247ai-backend", description="OpenTelemetry service name"
    )

    # OpenTelemetry Traces Settings
    otel_exporter_otlp_traces_endpoint: Optional[str] = Field(
        default=None, description="OTLP traces endpoint"
    )
    otel_exporter_otlp_traces_headers: Optional[str] = Field(
        default=None, description="OTLP traces headers"
    )
    otel_exporter_otlp_traces_protocol: str = Field(
        default="http/protobuf", description="OTLP traces protocol"
    )
    otel_exporter_otlp_traces_insecure: bool = Field(
        default=False, description="OTLP traces insecure mode"
    )

    # OpenTelemetry Metrics Settings
    otel_exporter_otlp_metrics_endpoint: Optional[str] = Field(
        default=None, description="OTLP metrics endpoint"
    )
    otel_exporter_otlp_metrics_headers: Optional[str] = Field(
        default=None, description="OTLP metrics headers"
    )
    otel_exporter_otlp_metrics_protocol: str = Field(
        default="http/protobuf", description="OTLP metrics protocol"
    )
    otel_exporter_otlp_metrics_insecure: bool = Field(
        default=False, description="OTLP metrics insecure mode"
    )

    # OpenTelemetry Logs Settings
    otel_exporter_otlp_logs_endpoint: Optional[str] = Field(
        default=None, description="OTLP logs endpoint"
    )
    otel_exporter_otlp_logs_headers: Optional[str] = Field(
        default=None, description="OTLP logs headers"
    )
    otel_exporter_otlp_logs_protocol: str = Field(
        default="http/protobuf", description="OTLP logs protocol"
    )
    otel_exporter_otlp_logs_insecure: bool = Field(
        default=False, description="OTLP logs insecure mode"
    )

    # Voice WebSocket (Pipecat) public URLs
    # Browser-reachable WebSocket base for voice-ws (no path; /ws is appended)
    voice_ws_public_url: str = Field(
        default="ws://localhost:7860",
        description="Public WebSocket base URL for the voice-ws service",
    )
    # Twilio Media Streams require a publicly reachable wss:// URL (e.g. ngrok).
    # Falls back to voice_ws_public_url only when that URL is already public wss.
    voice_ws_twilio_url: str = Field(
        default="",
        description=(
            "Public wss:// base URL Twilio uses for Media Streams "
            "(e.g. wss://abc.ngrok-free.app). Empty means derive from "
            "VOICE_WS_PUBLIC_URL when non-localhost."
        ),
    )

    # Call recording and private object storage
    voice_recording_enabled: bool = Field(
        default=False,
        description="Capture and persist mixed call audio when consent is configured",
    )
    recording_storage_backend: Literal["local", "r2"] = Field(
        default="local",
        description="Private call-recording storage backend",
    )
    recording_storage_local_root: str = Field(
        default=".local-data/call-recordings",
        description="Ignored local recording directory for development",
    )
    recording_r2_endpoint: Optional[str] = Field(
        default=None,
        description="Cloudflare R2 S3-compatible endpoint",
    )
    recording_r2_bucket: Optional[str] = Field(
        default=None,
        description="Environment-specific private R2 bucket",
    )
    recording_r2_access_key_id: Optional[str] = Field(
        default=None,
        description="Bucket-scoped R2 access key ID",
    )
    recording_r2_secret_access_key: Optional[str] = Field(
        default=None,
        description="Bucket-scoped R2 secret access key",
    )
    recording_r2_presign_ttl_seconds: int = Field(
        default=300,
        ge=1,
        le=604800,
        description="Lifetime of an R2 recording playback URL",
    )
    recording_encryption_mode: Literal["provider_managed", "customer_managed"] = Field(
        default="provider_managed",
        description="Recording encryption strategy; customer mode is reserved",
    )
    recording_retention_days: int = Field(
        default=90,
        ge=1,
        le=3650,
        description="Days before a recording becomes eligible for cleanup",
    )

    # Token Refresh Service Settings
    token_refresh_check_interval_minutes: int = Field(
        default=5,
        ge=1,
        le=60,
        description="Interval in minutes to check tokens for refresh (default: 5)",
    )
    token_refresh_expiry_window_minutes: int = Field(
        default=15,
        ge=1,
        le=60,
        description="Window in minutes before expiry to refresh tokens (default: 15)",
    )
    token_refresh_attention_window_minutes: int = Field(
        default=30,
        ge=1,
        le=1440,
        description=(
            "Window in minutes before expiry to notify administrators when a "
            "connection cannot be renewed automatically (default: 30)."
        ),
    )
    token_refresh_lock_lease_seconds: int = Field(
        default=180,
        ge=180,
        le=600,
        description=(
            "TTL (seconds) of the per-tool refresh lease lock. Must remain "
            "at least 180 seconds to outlive the 105-second OAuth request deadline, "
            "bounded DNS validation, and credential persistence (default: 180)."
        ),
    )
    token_refresh_max_concurrent_refreshes: int = Field(
        default=5,
        ge=1,
        le=20,
        description=(
            "Max number of OAuth refresh round-trips to run in parallel per "
            "cycle. Higher values refresh faster but load providers more (default: 5)."
        ),
    )

    # Twilio Settings
    twilio_account_sid: Optional[str] = Field(
        default=None, description="Twilio Account SID"
    )
    twilio_auth_token: Optional[str] = Field(
        default=None, description="Twilio Auth Token"
    )
    twilio_phone_number_sid: Optional[str] = Field(
        default=None, description="Default Twilio phone number SID"
    )
    twilio_sms_from_number: Optional[str] = Field(
        default=None,
        description="Twilio E.164 sender number used for platform SMS alerts",
    )
    twilio_whatsapp_from_number: Optional[str] = Field(
        default=None,
        description="Twilio WhatsApp-enabled sender in E.164 format",
    )
    twilio_whatsapp_content_sid: Optional[str] = Field(
        default=None,
        description="Approved Twilio WhatsApp Content template SID for lead alerts",
    )
    twilio_webhook_signature_validation_enabled: bool = Field(
        default=True,
        description="Validate X-Twilio-Signature on inbound and status webhooks",
    )

    @validator("cors_origins", pre=True)
    def parse_cors_origins(cls, v):
        """Parse CORS origins from environment variable string."""
        if isinstance(v, str):
            # Try to parse as JSON array first
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                # If not valid JSON, split by comma and strip whitespace
                return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @validator("platform_admin_allowlist", pre=True)
    def parse_admin_allowlist(cls, v):
        """Parse the allowlist from a comma-separated string; normalize case."""
        if isinstance(v, str):
            return [email.strip().lower() for email in v.split(",") if email.strip()]
        if isinstance(v, list):
            return [str(email).strip().lower() for email in v if str(email).strip()]
        return v

    class Config:
        env_file = str(PROJECT_ROOT / ".env.local")
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "allow"  # Allow extra fields that are not explicitly defined


# Global settings instance
settings = Settings()
