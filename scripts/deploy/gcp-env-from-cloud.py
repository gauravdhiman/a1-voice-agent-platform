#!/usr/bin/env python3
"""Generate Cloud Run / VM env YAML from .env.prod for a given service.

The ``backend`` service runs on GCP Cloud Run; the ``voice-ws`` service runs on
the OCI VM (Pipecat WebSocket worker). Both read from the same ``.env.prod``.
"""

from __future__ import annotations

import argparse
import json
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
        env[key.strip()] = value.strip()
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
        raise ValueError(
            "enabled R2 recording requires: " + ", ".join(missing)
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


BACKEND_KEYS = {
    "APP_NAME",
    "APP_BASE_URL",
    "ENVIRONMENT",
    "DEBUG",
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
} | RECORDING_KEYS

# voice-ws (Pipecat WebSocket worker) env keys.
# voice-ws verifies the voice_ws_session JWT issued by the backend, so it MUST
# share JWT_SECRET_KEY. It fetches agent tools directly from Supabase (no session
# manager), so it needs the Supabase service key, not DATABASE_URL.
WORKER_KEYS = {
    "ENVIRONMENT",
    "DEBUG",
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
} | RECORDING_KEYS


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
    except ValueError as exc:
        print(f"Invalid recording configuration: {exc}", file=sys.stderr)
        return 2
    keys = BACKEND_KEYS if args.service == "backend" else WORKER_KEYS
    sys.stdout.write(to_yaml(env, keys))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
