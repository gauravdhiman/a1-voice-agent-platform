"""Shared deployment secret inventory and naming rules.

This module deliberately contains names and policy, never secret values.  The
same inventory is used by the GCP Secret Manager deploy path and the OCI Vault
voice-ws bootstrap so a new credential cannot silently fall back to a plaintext
deployment file on only one runtime.
"""

from __future__ import annotations

import re
from pathlib import Path

# Values which must not be copied into a server environment file or an OCI
# public deployment manifest.  Browser-only values may still be listed here so
# CI keeps them out of the non-secret deployment config; the frontend build
# consumes them explicitly as public browser configuration.
SECRET_KEYS = frozenset(
    {
        "SUPABASE_SERVICE_KEY",
        "SUPABASE_ANON_KEY",
        "NEXT_PUBLIC_SUPABASE_ANON_KEY",
        "DATABASE_URL",
        "ENCRYPTION_KEY",
        "ENCRYPTION_KEY_FALLBACKS",
        "JWT_SECRET_KEY",
        "STRIPE_SECRET_KEY",
        "STRIPE_WEBHOOK_SECRET",
        "TURNSTILE_SECRET_KEY",
        "RESEND_API_KEY",
        "GOOGLE_OAUTH_TOOL_CLIENT_SECRET",
        "SUPABASE_AUTH_EXTERNAL_GOOGLE_CLIENT_SECRET",
        "SUPABASE_AUTH_EXTERNAL_LINKEDIN_OIDC_CLIENT_SECRET",
        "RECORDING_R2_ACCESS_KEY_ID",
        "RECORDING_R2_SECRET_ACCESS_KEY",
        "GEMINI_API_KEY",
        "DEEPGRAM_API_KEY",
        "OPENAI_API_KEY",
        "CARTESIA_API_KEY",
        "CEREBRAS_API_KEY",
        "OPENROUTER_API_KEY",
        "FISH_API_KEY",
        "TWILIO_AUTH_TOKEN",
        "MCP_OAUTH_CLIENT_SECRET",
        "MCP_OAUTH_STATE_SECRET",
        "OTEL_EXPORTER_OTLP_TRACES_HEADERS",
        "OTEL_EXPORTER_OTLP_METRICS_HEADERS",
        "OTEL_EXPORTER_OTLP_LOGS_HEADERS",
    }
)


BACKEND_SECRET_KEYS = frozenset(
    {
        "SUPABASE_SERVICE_KEY",
        "SUPABASE_ANON_KEY",
        "DATABASE_URL",
        "ENCRYPTION_KEY",
        "ENCRYPTION_KEY_FALLBACKS",
        "JWT_SECRET_KEY",
        "STRIPE_SECRET_KEY",
        "STRIPE_WEBHOOK_SECRET",
        "TURNSTILE_SECRET_KEY",
        "RESEND_API_KEY",
        "GOOGLE_OAUTH_TOOL_CLIENT_SECRET",
        "SUPABASE_AUTH_EXTERNAL_GOOGLE_CLIENT_SECRET",
        "SUPABASE_AUTH_EXTERNAL_LINKEDIN_OIDC_CLIENT_SECRET",
        "RECORDING_R2_ACCESS_KEY_ID",
        "RECORDING_R2_SECRET_ACCESS_KEY",
        "GEMINI_API_KEY",
        "TWILIO_AUTH_TOKEN",
        "MCP_OAUTH_CLIENT_SECRET",
        "MCP_OAUTH_STATE_SECRET",
        "OTEL_EXPORTER_OTLP_TRACES_HEADERS",
        "OTEL_EXPORTER_OTLP_METRICS_HEADERS",
        "OTEL_EXPORTER_OTLP_LOGS_HEADERS",
    }
)


WORKER_SECRET_KEYS = frozenset(
    {
        "SUPABASE_SERVICE_KEY",
        "SUPABASE_ANON_KEY",
        "ENCRYPTION_KEY",
        "ENCRYPTION_KEY_FALLBACKS",
        "JWT_SECRET_KEY",
        "RECORDING_R2_ACCESS_KEY_ID",
        "RECORDING_R2_SECRET_ACCESS_KEY",
        "GEMINI_API_KEY",
        "DEEPGRAM_API_KEY",
        "OPENAI_API_KEY",
        "CARTESIA_API_KEY",
        "CEREBRAS_API_KEY",
        "OPENROUTER_API_KEY",
        "FISH_API_KEY",
        "TWILIO_AUTH_TOKEN",
        "OTEL_EXPORTER_OTLP_TRACES_HEADERS",
        "OTEL_EXPORTER_OTLP_METRICS_HEADERS",
        "OTEL_EXPORTER_OTLP_LOGS_HEADERS",
    }
)


SERVICE_SECRET_KEYS = {
    "backend": BACKEND_SECRET_KEYS,
    "voice-ws": WORKER_SECRET_KEYS,
}

SERVICE_REQUIRED_SECRET_KEYS = {
    "backend": frozenset(
        {
            "SUPABASE_SERVICE_KEY",
            "SUPABASE_ANON_KEY",
            "DATABASE_URL",
            "ENCRYPTION_KEY",
            "JWT_SECRET_KEY",
            "GEMINI_API_KEY",
        }
    ),
    "voice-ws": frozenset(
        {
            "ENCRYPTION_KEY",
            "JWT_SECRET_KEY",
            "SUPABASE_SERVICE_KEY",
            "GEMINI_API_KEY",
        }
    ),
}


def validate_production_stripe_credentials(
    env: dict[str, str], *, production: bool
) -> None:
    """Reject Stripe test-mode credentials on a production secret path."""

    if not production:
        return

    credentials = {
        "STRIPE_SECRET_KEY": ("sk_test_", "sk_live_"),
        "NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY": ("pk_test_", "pk_live_"),
    }
    for key, (test_prefix, live_prefix) in credentials.items():
        value = env.get(key, "").strip()
        if value.startswith(test_prefix):
            raise ValueError(
                f"refusing to use a test Stripe credential in production: {key} "
                f"must use {live_prefix}"
            )


# The worker deployment needs these values to locate OCI Vault, but they are
# identifiers and not secret material.  They are emitted only into the
# short-lived public manifest used by the remote bootstrap helper.
PUBLIC_WORKER_METADATA_KEYS = frozenset(
    {
        "OCI_VAULT_ID",
        "OCI_SECRET_NAME_PREFIX",
    }
)


def parse_env_file(path: Path) -> dict[str, str]:
    """Parse the repository's simple ``KEY=value`` deployment format.

    The parser intentionally does not expand variables or execute shell code.
    Surrounding single or double quotes are removed to match the existing
    deployment scripts.
    """

    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
            value = value[1:-1]
        values[key.strip()] = value
    return values


def normalize_secret_id(prefix: str, key: str) -> str:
    """Return the stable Secret Manager / OCI Vault name for an env key."""

    normalized_prefix = re.sub(r"[^a-z0-9-]+", "-", prefix.strip().lower())
    normalized_prefix = re.sub(r"-+", "-", normalized_prefix).strip("-")
    normalized_key = re.sub(r"[^a-z0-9-]+", "-", key.strip().lower())
    normalized_key = re.sub(r"-+", "-", normalized_key).strip("-")
    if not normalized_prefix or not normalized_key:
        raise ValueError("secret name prefix and key must contain a-z or 0-9")
    name = f"{normalized_prefix}-{normalized_key}"
    if len(name) > 255:
        raise ValueError(f"secret name is too long: {name[:80]}...")
    return name


def service_secret_keys(service: str) -> frozenset[str]:
    """Return the secret inventory required by a deployable service."""

    try:
        return SERVICE_SECRET_KEYS[service]
    except KeyError as exc:
        raise ValueError(f"unsupported service: {service}") from exc


def configured_secret_keys(env: dict[str, str], service: str) -> list[str]:
    """Return configured service secrets in deterministic order.

    Optional provider integrations are allowed to omit their secret.  Required
    runtime settings are validated by the existing service-specific startup
    and deployment checks after rendering.
    """

    return sorted(
        key for key in service_secret_keys(service) if env.get(key, "").strip()
    )


def requested_secret_keys(env: dict[str, str], service: str) -> list[str]:
    """Return required secrets plus optional keys explicitly present in config.

    An empty ``KEY=`` entry is an intentional opt-in for an optional managed
    secret. Omitting the key prevents a stale manager version from being
    injected into a runtime.
    """

    required = SERVICE_REQUIRED_SECRET_KEYS[service]
    return sorted(
        key for key in service_secret_keys(service) if key in env or key in required
    )


def public_worker_keys() -> frozenset[str]:
    """Return non-secret worker values needed before OCI Vault is queried."""

    return PUBLIC_WORKER_METADATA_KEYS
