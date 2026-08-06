#!/usr/bin/env python3
"""Generate Cloud Run / VM env YAML from .env.cloud for a given service.

The ``backend`` service runs on GCP Cloud Run; the ``voice-ws`` service runs on
the OCI VM (Pipecat WebSocket worker). Both read from the same ``.env.cloud``.
"""

from __future__ import annotations

import argparse
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
}

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
}


def to_yaml(env: dict[str, str], keys: set[str]) -> str:
    lines: list[str] = []
    for key in sorted(keys):
        if key not in env or env[key] == "":
            continue
        value = env[key].replace('"', '\\"')
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
        default=".env.cloud",
        help="Path to cloud env file (default: .env.cloud)",
    )
    args = parser.parse_args()
    path = Path(args.env_file)
    if not path.exists():
        print(f"Missing {path}", file=sys.stderr)
        return 1
    env = parse_env_file(path)
    keys = BACKEND_KEYS if args.service == "backend" else WORKER_KEYS
    sys.stdout.write(to_yaml(env, keys))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
