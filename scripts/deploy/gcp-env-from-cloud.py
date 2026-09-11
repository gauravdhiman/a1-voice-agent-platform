#!/usr/bin/env python3
"""Generate Cloud Run / VM env YAML from .env.prod for a given service.

The ``backend`` service runs on GCP Cloud Run; the ``voice-ws`` service runs on
the OCI VM (Pipecat WebSocket worker). Both read from the same ``.env.prod``.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def parse_env_file(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        value = value.strip()
        # Match dotenv behavior for quoted secrets (Basic auth values and
        # encrypted keys commonly contain punctuation that should remain
        # untouched after the surrounding quotes are removed).
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
            value = value[1:-1]
        env[key.strip()] = value
    return env


def validate_recording_configuration(env: dict[str, str]) -> None:
    """Fail deployment early when enabled R2 recording lacks credentials.

    Args:
        env: Parsed environment values that will be emitted to a service.

    Raises:
        ValueError: If recording is enabled with the R2 backend but one or
            more required bucket connection values are empty.
    """
    recording_enabled = any(
        env.get(key, "").strip().lower() == "true"
        for key in ("VOICE_RECORDING_ENABLED", "VOICE_RECORDING_TEE")
    )
    if not recording_enabled or env.get("RECORDING_STORAGE_BACKEND", "local") != "r2":
        return

    required = (
        "RECORDING_R2_ENDPOINT",
        "RECORDING_R2_BUCKET",
        "RECORDING_R2_ACCESS_KEY_ID",
        "RECORDING_R2_SECRET_ACCESS_KEY",
    )
    missing = [key for key in required if not env.get(key, "").strip()]
    if missing:
        raise ValueError("enabled R2 recording requires: " + ", ".join(missing))


def validate_encryption_configuration(env: dict[str, str]) -> None:
    """Fail deployment when server-side encryption has no current key.

    Args:
        env: Parsed environment values that will be emitted to a server.

    Raises:
        ValueError: If the current Fernet key is missing or empty.
    """
    if not env.get("ENCRYPTION_KEY", "").strip():
        raise ValueError("server-side encryption requires: ENCRYPTION_KEY")


_OTEL_SIGNALS = ("TRACES", "METRICS", "LOGS")
_PLACEHOLDER = re.compile(
    r"(?:placeholder|replace[-_]?with|your[-_]|example(?:[-_]|$)|changeme|dummy)",
    re.IGNORECASE,
)


def _is_placeholder(value: str) -> bool:
    """Return whether a deployment value is visibly an example placeholder."""
    return not value.strip() or bool(_PLACEHOLDER.search(value))


def validate_observability_configuration(env: dict[str, str]) -> None:
    """Validate the opt-in production telemetry contract before deployment.

    Disabled staging/local deployments intentionally skip this check. Once
    enabled, each signal must have its own OTLP/HTTP endpoint and auth header;
    production endpoints must use HTTPS and cannot remain example values.

    Args:
        env: Parsed deployment environment values.

    Raises:
        ValueError: If enabled telemetry is incomplete or unsafe for production.
    """
    if env.get("OTEL_ENABLED", "").strip().lower() != "true":
        return

    missing: list[str] = []
    for signal in _OTEL_SIGNALS:
        for suffix in ("ENDPOINT", "PROTOCOL", "HEADERS"):
            key = f"OTEL_EXPORTER_OTLP_{signal}_{suffix}"
            if _is_placeholder(env.get(key, "")):
                missing.append(key)
    if missing:
        raise ValueError(
            "enabled OpenTelemetry requires configured signal values: "
            + ", ".join(missing)
        )

    environment = env.get("ENVIRONMENT", "").strip().lower()
    if environment in {"production", "prod"}:
        non_http = [
            f"OTEL_EXPORTER_OTLP_{signal}_PROTOCOL"
            for signal in _OTEL_SIGNALS
            if env[f"OTEL_EXPORTER_OTLP_{signal}_PROTOCOL"].strip().lower()
            != "http/protobuf"
        ]
        insecure = [
            f"OTEL_EXPORTER_OTLP_{signal}_INSECURE"
            for signal in _OTEL_SIGNALS
            if env.get(f"OTEL_EXPORTER_OTLP_{signal}_INSECURE", "").strip().lower()
            == "true"
        ]
        non_https = [
            f"OTEL_EXPORTER_OTLP_{signal}_ENDPOINT"
            for signal in _OTEL_SIGNALS
            if not env[f"OTEL_EXPORTER_OTLP_{signal}_ENDPOINT"]
            .strip()
            .lower()
            .startswith("https://")
        ]
        if non_http or insecure or non_https:
            unsafe = non_http + insecure + non_https
            raise ValueError(
                "production cloud OpenTelemetry requires http/protobuf over "
                "HTTPS with secure transport: " + ", ".join(unsafe)
            )


def normalize_cors_origins(value: str) -> str:
    """Normalize CORS origins to the JSON string expected by Pydantic settings.

    GitHub multiline environment secrets can contain either a valid JSON list
    or a loosely formatted bracketed list. Cloud Run must receive the list as
    a string containing quoted JSON values, so normalize both forms before
    rendering the deployment environment file.

    Args:
        value: Raw CORS_ORIGINS value from the deployment environment file.

    Returns:
        A JSON-encoded list when the value is a list, otherwise the original
        value unchanged.
    """
    stripped = value.strip()
    if not (stripped.startswith("[") and stripped.endswith("]")):
        return value

    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        items = [
            item.strip().strip("\\\"'")
            for item in stripped[1:-1].split(",")
            if item.strip()
        ]
        return json.dumps(items)

    if isinstance(parsed, list):
        return json.dumps(parsed)
    return value


# Recording configuration must be available to both the backend (playback and
# artifact metadata) and voice-ws (capture and upload). Keep this shared set in
# one place so a new deployment target cannot silently omit part of the
# storage contract.
RECORDING_KEYS = {
    "VOICE_RECORDING_ENABLED",
    "VOICE_RECORDING_TEE",
    "RECORDING_STORAGE_BACKEND",
    "RECORDING_STORAGE_LOCAL_ROOT",
    "RECORDING_ENCRYPTION_MODE",
    "RECORDING_RETENTION_DAYS",
    "RECORDING_R2_ENDPOINT",
    "RECORDING_R2_BUCKET",
    "RECORDING_R2_ACCESS_KEY_ID",
    "RECORDING_R2_SECRET_ACCESS_KEY",
    "RECORDING_R2_PRESIGN_TTL_SECONDS",
}


OBSERVABILITY_KEYS = {
    "OTEL_ENABLED",
    "OTEL_SERVICE_NAME",
    "OTEL_SERVICE_VERSION",
    "OTEL_TRACES_SAMPLER_ARG",
    *(
        f"OTEL_EXPORTER_OTLP_{signal}_{field}"
        for signal in ("TRACES", "METRICS", "LOGS")
        for field in ("ENDPOINT", "PROTOCOL", "HEADERS", "INSECURE")
    ),
}


SERVICE_OTEL_NAMES = {
    "backend": ("OTEL_BACKEND_SERVICE_NAME", "247ai-backend"),
    "voice-ws": ("OTEL_VOICE_WS_SERVICE_NAME", "247ai-voice-ws"),
}

BACKEND_KEYS = (
    {
        "APP_NAME",
        "APP_BASE_URL",
        "ENVIRONMENT",
        "DEBUG",
        # Fernet credentials protect organization provider keys and OAuth tokens.
        # They must reach every server-side runtime; omitting them makes existing
        # encrypted data unreadable and causes all new encrypted writes to fail.
        "ENCRYPTION_KEY",
        "ENCRYPTION_KEY_FALLBACKS",
        "CORS_ORIGINS",
        "SUPABASE_URL",
        "SUPABASE_SERVICE_KEY",
        "SUPABASE_ANON_KEY",
        "DATABASE_URL",
        "JWT_SECRET_KEY",
        "STRIPE_SECRET_KEY",
        "STRIPE_WEBHOOK_SECRET",
        "TWILIO_ACCOUNT_SID",
        "TWILIO_AUTH_TOKEN",
        "TWILIO_PHONE_NUMBER_SID",
        "RESEND_API_KEY",
        "RESEND_FROM_EMAIL",
        "RESEND_FROM_NAME",
        "GOOGLE_OAUTH_TOOL_CLIENT_ID",
        "GOOGLE_OAUTH_TOOL_CLIENT_SECRET",
        "GOOGLE_OAUTH_TOOL_REDIRECT_URI",
        "SUPABASE_AUTH_EXTERNAL_LINKEDIN_OIDC_CLIENT_ID",
        "SUPABASE_AUTH_EXTERNAL_LINKEDIN_OIDC_CLIENT_SECRET",
        "LINKEDIN_OAUTH_SCOPES",
        "GEMINI_API_KEY",
        # Voice transport (Pipecat WebSocket). Backend builds the browser wsUrl and
        # the Twilio Media Streams URL from these settings.
        "VOICE_TRANSPORT",
        "VOICE_WS_PUBLIC_URL",
        "VOICE_WS_TWILIO_URL",
        "TOKEN_REFRESH_CHECK_INTERVAL_MINUTES",
        "TOKEN_REFRESH_EXPIRY_WINDOW_MINUTES",
        "OTEL_ENABLED",
        "OTEL_SERVICE_NAME",
        "OTEL_PYTHON_FASTAPI_EXCLUDED_URLS",
        "MCP_ALLOW_LOCAL_URLS",
        "PYTHONPATH",
    }
    | RECORDING_KEYS
    | OBSERVABILITY_KEYS
)

# voice-ws (Pipecat WebSocket worker) env keys.
# voice-ws verifies the voice_ws_session JWT issued by the backend, so it MUST
# share JWT_SECRET_KEY. It fetches agent tools directly from Supabase (no session
# manager), so it needs the Supabase service key, not DATABASE_URL.
WORKER_KEYS = (
    {
        "ENVIRONMENT",
        "DEBUG",
        # Keep the worker's decryption keyring aligned with the backend so it can
        # resolve organization provider credentials and OAuth-backed tools.
        "ENCRYPTION_KEY",
        "ENCRYPTION_KEY_FALLBACKS",
        "SUPABASE_URL",
        "SUPABASE_SERVICE_KEY",
        "SUPABASE_ANON_KEY",
        "JWT_SECRET_KEY",
        "VOICE_TRANSPORT",
        "GEMINI_API_KEY",
        "AGENT_DEFAULT_TIMEZONE",
        "OTEL_ENABLED",
        "DEEPGRAM_API_KEY",
        "OPENAI_API_KEY",
        "CARTESIA_API_KEY",
        "CEREBRAS_API_KEY",
        "OPENROUTER_API_KEY",
        "FISH_API_KEY",
        "MCP_ALLOW_LOCAL_URLS",
        "PYTHONPATH",
    }
    | RECORDING_KEYS
    | OBSERVABILITY_KEYS
)


def to_yaml(env: dict[str, str], keys: set[str]) -> str:
    lines: list[str] = []
    for key in sorted(keys):
        if key not in env or env[key] == "":
            continue
        value = env[key].replace('"', '\\"')
        if key == "CORS_ORIGINS":
            value = normalize_cors_origins(env[key]).replace("'", "''")
            lines.append(f"{key}: '{value}'")
        else:
            lines.append(f'{key}: "{value}"')
    # Cloud Run backend/worker use /app with shared module
    if "PYTHONPATH" in keys and "PYTHONPATH" not in env:
        lines.append('PYTHONPATH: "/app"')
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("service", choices=["backend", "voice-ws"])
    parser.add_argument(
        "--env-file",
        default=".env.prod",
        help="Path to cloud env file (default: .env.prod)",
    )
    args = parser.parse_args()
    path = Path(args.env_file)
    if not path.exists():
        print(f"Missing {path}", file=sys.stderr)
        return 1
    env = parse_env_file(path)
    try:
        validate_recording_configuration(env)
        validate_encryption_configuration(env)
        validate_observability_configuration(env)
    except ValueError as exc:
        print(f"Invalid deployment configuration: {exc}", file=sys.stderr)
        return 2
    keys = BACKEND_KEYS if args.service == "backend" else WORKER_KEYS
    service_env = dict(env)
    service_name_key, default_service_name = SERVICE_OTEL_NAMES[args.service]
    service_env["OTEL_SERVICE_NAME"] = env.get(
        service_name_key,
        env.get("OTEL_SERVICE_NAME", default_service_name),
    )
    sys.stdout.write(to_yaml(service_env, keys))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
