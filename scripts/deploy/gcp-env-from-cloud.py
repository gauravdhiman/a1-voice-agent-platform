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

try:
    from secret_config import (
        BACKEND_SECRET_KEYS,
        PUBLIC_WORKER_METADATA_KEYS,
        SECRET_KEYS,
        WORKER_SECRET_KEYS,
        normalize_secret_id,
        requested_secret_keys,
    )
except ModuleNotFoundError:  # pragma: no cover - supports direct test imports
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from secret_config import (
        BACKEND_SECRET_KEYS,
        PUBLIC_WORKER_METADATA_KEYS,
        SECRET_KEYS,
        WORKER_SECRET_KEYS,
        normalize_secret_id,
        requested_secret_keys,
    )


def parse_env_file(path: Path) -> dict[str, str]:
    """Parse deployment values without sourcing or expanding shell code."""

    env: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
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
        "API_BASE_URL",
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
        "TWILIO_SMS_FROM_NUMBER",
        "TWILIO_WEBHOOK_SIGNATURE_VALIDATION_ENABLED",
        "RESEND_API_KEY",
        "EMAIL_PROVIDER",
        "RESEND_FROM_EMAIL",
        "RESEND_FROM_NAME",
        "PUBLIC_SIGNUP_ENABLED",
        "PLATFORM_ADMIN_ALLOWLIST",
        "PHONE_NUMBER_BILLING_CHECK_INTERVAL_HOURS",
        "PHONE_NUMBER_BILLING_GRACE_PERIOD_DAYS",
        "PHONE_NUMBER_RELEASE_RETRY_INTERVAL_HOURS",
        "NOTIFICATION_RETRY_CHECK_INTERVAL_HOURS",
        "NOTIFICATION_RETRY_CHECK_INTERVAL_MINUTES",
        "TURNSTILE_SECRET_KEY",
        "GOOGLE_OAUTH_TOOL_CLIENT_ID",
        "GOOGLE_OAUTH_TOOL_CLIENT_SECRET",
        "GOOGLE_OAUTH_TOOL_REDIRECT_URI",
        "SUPABASE_AUTH_EXTERNAL_GOOGLE_CLIENT_ID",
        "SUPABASE_AUTH_EXTERNAL_GOOGLE_CLIENT_SECRET",
        "SUPABASE_AUTH_EXTERNAL_LINKEDIN_OIDC_CLIENT_ID",
        "SUPABASE_AUTH_EXTERNAL_LINKEDIN_OIDC_CLIENT_SECRET",
        "LINKEDIN_OAUTH_SCOPES",
        "NEXT_PUBLIC_GOOGLE_CLIENT_ID",
        "GEMINI_API_KEY",
        # Voice transport (Pipecat WebSocket). Backend builds the browser wsUrl and
        # the Twilio Media Streams URL from these settings.
        "VOICE_TRANSPORT",
        "VOICE_WS_PUBLIC_URL",
        "VOICE_WS_TWILIO_URL",
        "TOKEN_REFRESH_CHECK_INTERVAL_MINUTES",
        "TOKEN_REFRESH_EXPIRY_WINDOW_MINUTES",
        "TOKEN_REFRESH_ATTENTION_WINDOW_MINUTES",
        "OTEL_ENABLED",
        "OTEL_SERVICE_NAME",
        "OTEL_PYTHON_FASTAPI_EXCLUDED_URLS",
        "MCP_ALLOW_LOCAL_URLS",
        "MCP_OAUTH_CLIENT_ID",
        "MCP_OAUTH_CLIENT_SECRET",
        "MCP_OAUTH_REDIRECT_URI",
        "PYTHONPATH",
    }
    | BACKEND_SECRET_KEYS
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
        "MCP_HOST",
        "MCP_PORT",
        "OTEL_ENABLED",
        "DEEPGRAM_API_KEY",
        "OPENAI_API_KEY",
        "CARTESIA_API_KEY",
        "CEREBRAS_API_KEY",
        "OPENROUTER_API_KEY",
        "FISH_API_KEY",
        "TWILIO_ACCOUNT_SID",
        "MCP_ALLOW_LOCAL_URLS",
        "PYTHONPATH",
    }
    | WORKER_SECRET_KEYS
    | RECORDING_KEYS
    | OBSERVABILITY_KEYS
)


def _should_emit(key: str, env: dict[str, str], secret_mode: str) -> bool:
    """Return whether a key belongs in the generated service environment."""

    return bool(env.get(key, "")) and (secret_mode == "env" or key not in SECRET_KEYS)


def to_yaml(env: dict[str, str], keys: set[str], secret_mode: str = "env") -> str:
    lines: list[str] = []
    for key in sorted(keys):
        if not _should_emit(key, env, secret_mode):
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


def _dotenv_value(value: str) -> str:
    """Quote a dotenv value without allowing shell interpolation."""

    if "\n" in value or "\r" in value:
        raise ValueError("deployment dotenv values cannot contain newlines")
    if "'" not in value:
        return f"'{value}'"
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def to_dotenv(
    env: dict[str, str], keys: set[str], secret_mode: str, *, public_worker: bool
) -> str:
    """Render a dotenv file for the OCI bootstrap or local inspection."""

    output_keys = set(keys)
    if public_worker:
        output_keys.update(PUBLIC_WORKER_METADATA_KEYS)
    lines: list[str] = []
    for key in sorted(output_keys):
        if (
            not _should_emit(key, env, secret_mode)
            and key not in PUBLIC_WORKER_METADATA_KEYS
        ):
            continue
        if not env.get(key, ""):
            continue
        lines.append(f"{key}={_dotenv_value(env[key])}")
    return "\n".join(lines) + "\n"


def to_secret_manifest(service: str, prefix: str, env: dict[str, str]) -> str:
    """Render an env-key to Vault-secret-name manifest without values."""

    lines = [
        f"{key}={normalize_secret_id(prefix, key)}"
        for key in requested_secret_keys(env, service)
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("service", choices=["backend", "voice-ws"])
    parser.add_argument(
        "--env-file",
        default=".env.prod",
        help="Path to cloud env file (default: .env.prod)",
    )
    parser.add_argument(
        "--secret-mode",
        choices=["env", "gcp", "public"],
        default=None,
        help=(
            "env includes values; gcp/public omit secret values. Defaults to "
            "SECRET_MANAGER_MODE from the env file or env."
        ),
    )
    parser.add_argument("--format", choices=["yaml", "dotenv"], default="yaml")
    parser.add_argument(
        "--secret-manifest",
        action="store_true",
        help="Render a value-free secret-name manifest for the OCI Vault bootstrap",
    )
    parser.add_argument(
        "--secret-prefix",
        help="Prefix used to derive managed secret names for --secret-manifest",
    )
    parser.add_argument(
        "--public-only",
        action="store_true",
        help="Render non-secret voice-ws settings plus OCI Vault metadata",
    )
    args = parser.parse_args()
    path = Path(args.env_file)
    if not path.exists():
        print(f"Missing {path}", file=sys.stderr)
        return 1
    env = parse_env_file(path)
    if args.secret_manifest:
        if args.service != "voice-ws":
            print("--secret-manifest is only supported for voice-ws", file=sys.stderr)
            return 2
        if not args.secret_prefix:
            print("--secret-prefix is required with --secret-manifest", file=sys.stderr)
            return 2
        try:
            sys.stdout.write(to_secret_manifest(args.service, args.secret_prefix, env))
        except ValueError as exc:
            print(f"Invalid secret manifest configuration: {exc}", file=sys.stderr)
            return 2
        return 0
    secret_mode = args.secret_mode or env.get("SECRET_MANAGER_MODE", "env").lower()
    output_format = args.format
    if args.public_only:
        secret_mode = "public"
        output_format = "dotenv"
    if secret_mode not in {"env", "gcp", "public"}:
        print(f"Invalid secret mode: {secret_mode}", file=sys.stderr)
        return 2
    try:
        # Public-only manifests intentionally do not contain the values needed
        # for sensitive validation; the remote OCI helper validates required
        # secret presence while rendering the final private env file.
        if secret_mode != "public":
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
    if output_format == "yaml":
        sys.stdout.write(to_yaml(service_env, keys, secret_mode))
    else:
        sys.stdout.write(
            to_dotenv(
                service_env,
                keys,
                secret_mode,
                public_worker=args.public_only and args.service == "voice-ws",
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
