#!/usr/bin/env bash

# Provision and run one complete, isolated development environment for the
# current Git worktree. Supabase CLI owns the local database/Auth/Storage
# containers; Docker Compose owns the application containers.
#
# Usage:
#   ./scripts/worktree-stack.sh config
#   ./scripts/worktree-stack.sh up
#   ./scripts/worktree-stack.sh status
#   ./scripts/worktree-stack.sh down
#   ./scripts/worktree-stack.sh purge --yes

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_DIR_DEFAULT="${ROOT}/.worktree-state"
SUPABASE_CLI="${SUPABASE_CLI:-supabase}"

COMMAND="help"
NAME_OVERRIDE=""
PORT_OFFSET_OVERRIDE=""
SOURCE_ENV_OVERRIDE=""
STATE_DIR="${STATE_DIR_DEFAULT}"
CONFIRM_PURGE=false
SKIP_MASTER_DATA=false

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

usage() {
  cat <<'EOF'
Usage: ./scripts/worktree-stack.sh COMMAND [OPTIONS]

Commands:
  config              Generate/inspect isolated ports and local Supabase config
  up                  Start local Supabase, migrate/seed, and start app services
  status              Show safe status and URLs for this worktree
  down                Stop app and Supabase containers while preserving data
  purge               Delete this worktree's containers, volumes, and state
                      (requires --yes; never use for a shared environment)

Options:
  --name NAME         Stable worktree name used in project IDs and credentials
  --port-offset N     Explicit non-zero host-port offset; default is deterministic
                      from this worktree path
  --source-env PATH   Copy provider settings from this env file and repair
                      placeholder values (defaults to this worktree's .env.local,
                      then the main checkout's .env.local, then the example)
  --state-dir PATH    Store generated config and credentials at this path
  --skip-master-data  Skip the explicit platform master-data synchronization
  --yes               Confirm destructive purge
  -h, --help          Show this help

Examples:
  ./scripts/worktree-stack.sh up
  ./scripts/worktree-stack.sh up --port-offset 60
  ./scripts/worktree-stack.sh status
  ./scripts/worktree-stack.sh down
  ./scripts/worktree-stack.sh purge --yes
EOF
}

die() {
  echo -e "${RED}Error: $*${NC}" >&2
  exit 1
}

absolute_path() {
  local path="$1"
  if [[ "$path" = /* ]]; then
    printf '%s' "$path"
  else
    printf '%s/%s' "$ROOT" "$path"
  fi
}

parse_args() {
  if [[ $# -gt 0 && "$1" != -* ]]; then
    COMMAND="$1"
    shift
  fi

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --name)
        [[ $# -ge 2 ]] || die "--name requires a value"
        NAME_OVERRIDE="$2"
        shift 2
        ;;
      --port-offset)
        [[ $# -ge 2 ]] || die "--port-offset requires a value"
        PORT_OFFSET_OVERRIDE="$2"
        shift 2
        ;;
      --source-env)
        [[ $# -ge 2 ]] || die "--source-env requires a value"
        SOURCE_ENV_OVERRIDE="$2"
        shift 2
        ;;
      --state-dir)
        [[ $# -ge 2 ]] || die "--state-dir requires a value"
        STATE_DIR="$2"
        shift 2
        ;;
      --skip-master-data)
        SKIP_MASTER_DATA=true
        shift
        ;;
      --yes)
        CONFIRM_PURGE=true
        shift
        ;;
      -h|--help|help)
        COMMAND="help"
        shift
        ;;
      *)
        die "unknown option: $1"
        ;;
    esac
  done

  STATE_DIR="$(absolute_path "$STATE_DIR")"
  if [[ -n "$SOURCE_ENV_OVERRIDE" ]]; then
    SOURCE_ENV_OVERRIDE="$(absolute_path "$SOURCE_ENV_OVERRIDE")"
  fi
}

set_env_value() {
  local file="$1"
  local key="$2"
  local value="$3"

  # Environment values can contain JSON, URLs, and shell metacharacters. Use
  # Python only for this small format-preserving edit instead of sourcing a
  # developer-controlled env file into this process.
  python3 - "$file" "$key" "$value" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
key = sys.argv[2]
value = sys.argv[3]
lines = path.read_text(encoding="utf-8").splitlines()
replacement = f"{key}={value}"
found = False
for index, line in enumerate(lines):
    if line.startswith(f"{key}="):
        lines[index] = replacement
        found = True
        break
if not found:
    if lines and lines[-1] != "":
        lines.append("")
    lines.append(replacement)
path.write_text("\n".join(lines) + "\n", encoding="utf-8")
PY
}

ensure_local_encryption_key() {
  local file="$1"
  local force_generate="${2:-false}"

  # Worktree app.env files are local, ignored state. Never copy the source
  # environment's encryption key into a new worktree: each isolated database
  # gets its own key, while an existing worktree keeps its key stable so its
  # encrypted credentials remain decryptable across restarts.
  if [[ "$force_generate" == true ]]; then
    python3 "$ROOT/scripts/ensure-local-encryption-key.py" "$file" --force
  else
    python3 "$ROOT/scripts/ensure-local-encryption-key.py" "$file"
  fi
}

read_env_value() {
  local file="$1"
  local key="$2"
  awk -F= -v name="$key" '$1 == name {
    sub(/^[^=]*=/, "")
    gsub(/^"|"$/, "")
    gsub(/^'"'"'|'"'"'$/, "")
    print
    exit
  }' "$file"
}

git_repository_root() {
  local common_dir
  common_dir="$(git -C "$ROOT" rev-parse --path-format=absolute --git-common-dir 2>/dev/null || true)"
  if [[ -z "$common_dir" ]]; then
    common_dir="$(git -C "$ROOT" rev-parse --git-common-dir 2>/dev/null || true)"
  fi
  if [[ -z "$common_dir" ]]; then
    printf '%s' "$ROOT"
    return 0
  fi

  if [[ "$common_dir" != /* ]]; then
    common_dir="$(cd "$ROOT/$common_dir" 2>/dev/null && pwd -P)" || {
      printf '%s' "$ROOT"
      return 0
    }
  fi
  dirname "$common_dir"
}

resolve_source_env() {
  if [[ -n "$SOURCE_ENV_OVERRIDE" ]]; then
    [[ -f "$SOURCE_ENV_OVERRIDE" ]] || die "source env does not exist: $SOURCE_ENV_OVERRIDE"
    printf '%s' "$SOURCE_ENV_OVERRIDE"
    return 0
  fi

  local repository_root candidate fallback
  repository_root="$(git_repository_root)"
  fallback=""
  for candidate in "$ROOT/.env.local" "$repository_root/.env.local"; do
    if [[ -f "$candidate" ]]; then
      [[ -n "$fallback" ]] || fallback="$candidate"
      if ! is_placeholder_env_value "$(read_env_value "$candidate" GEMINI_API_KEY)"; then
        printf '%s' "$candidate"
        return 0
      fi
    fi
  done

  if [[ -n "$fallback" ]]; then
    printf '%s' "$fallback"
    return 0
  fi

  [[ -f "$ROOT/.env.local.example" ]] || die "no source env found; expected .env.local or .env.local.example"
  printf '%s' "$ROOT/.env.local.example"
}

is_placeholder_env_value() {
  local value="${1:-}"
  local normalized
  normalized="$(printf '%s' "$value" | tr '[:upper:]' '[:lower:]')"

  [[ -z "$normalized" ]] && return 0
  [[ "$normalized" =~ [[:space:]] ]] && return 0
  case "$normalized" in
    *placeholder*|your-*|your_*|replace-*|replace_*|change-me*|changeme|example|example-*|dummy|dummy-*|test-key|test-key-*)
      return 0
      ;;
  esac
  return 1
}

sync_voice_provider_settings() {
  local source_env="$1"
  local key value
  for key in \
    GEMINI_API_KEY \
    DEEPGRAM_API_KEY \
    OPENAI_API_KEY \
    CARTESIA_API_KEY \
    CEREBRAS_API_KEY \
    OPENROUTER_API_KEY \
    FISH_API_KEY \
    RESEND_API_KEY \
    RESEND_FROM_EMAIL \
    RESEND_FROM_NAME; do
    value="$(read_env_value "$source_env" "$key")"
    if [[ -n "$value" ]] && ! is_placeholder_env_value "$value"; then
      set_env_value "$APP_ENV" "$key" "$value"
    fi
  done
}

require_gemini_api_key() {
  local source_env="$1"
  local app_key
  app_key="$(read_env_value "$APP_ENV" GEMINI_API_KEY)"
  if is_placeholder_env_value "$app_key"; then
    die "GEMINI_API_KEY is missing or still an example value in $APP_ENV; set a valid key in $source_env or pass --source-env"
  fi
}

derive_identity() {
  local requested_name
  requested_name="${NAME_OVERRIDE:-$(basename "$ROOT")}"
  local safe_name
  safe_name="$(printf '%s' "$requested_name" | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9' '-' | sed 's/^-*//; s/-*$//' | cut -c1-24)"
  [[ -n "$safe_name" ]] || safe_name="worktree"

  local checksum
  checksum="$(printf '%s' "$ROOT" | cksum | awk '{print $1}')"
  local suffix
  suffix="$(printf '%s' "$checksum" | tail -c 7)"
  WORKTREE_ID="${safe_name}-${suffix}"
  SUPABASE_PROJECT_ID="247ai-wt-${WORKTREE_ID}"
  APP_COMPOSE_PROJECT="247ai-wt-${WORKTREE_ID}"

  if [[ -n "$PORT_OFFSET_OVERRIDE" ]]; then
    PORT_OFFSET="$PORT_OFFSET_OVERRIDE"
  elif [[ -f "$STATE_DIR/metadata.env" ]]; then
    # Reconfiguration must not silently move an existing worktree to another
    # port slot. Keep the stored slot unless the caller explicitly supplies a
    # new --port-offset.
    local stored_port_offset
    stored_port_offset="$(awk -F= '$1 == "PORT_OFFSET" { print $2; exit }' "$STATE_DIR/metadata.env")"
    if [[ "$stored_port_offset" =~ ^[0-9]+$ ]] && (( stored_port_offset >= 1 )); then
      PORT_OFFSET="$stored_port_offset"
    else
      PORT_OFFSET=$((10 + (checksum % 90) * 10))
    fi
  else
    # Ten-port slots keep each app and Supabase service set together while
    # leaving enough room for many parallel worktrees. A collision is checked
    # by the caller before anything is started; --port-offset is the escape
    # hatch when another process already owns the deterministic slot.
    PORT_OFFSET=$((10 + (checksum % 90) * 10))
  fi

  if ! [[ "$PORT_OFFSET" =~ ^[0-9]+$ ]] || (( PORT_OFFSET < 1 || PORT_OFFSET > 10000 )); then
    die "port offset must be an integer from 1 through 10000 (received '$PORT_OFFSET')"
  fi

  APP_FRONTEND_PORT=$((3000 + PORT_OFFSET))
  APP_BACKEND_PORT=$((8000 + PORT_OFFSET))
  APP_VOICE_WS_PORT=$((7860 + PORT_OFFSET))
  OTEL_GRPC_PORT=$((4317 + PORT_OFFSET))
  OTEL_HTTP_PORT=$((4318 + PORT_OFFSET))
  OTEL_HEALTH_PORT=$((13133 + PORT_OFFSET))
  GRAFANA_PORT=$((3300 + PORT_OFFSET))
  PROMETHEUS_PORT=$((9090 + PORT_OFFSET))
  ALERTMANAGER_PORT=$((9093 + PORT_OFFSET))

  SUPABASE_SHADOW_PORT=$((54320 + PORT_OFFSET))
  SUPABASE_API_PORT=$((54321 + PORT_OFFSET))
  SUPABASE_DB_PORT=$((54322 + PORT_OFFSET))
  SUPABASE_STUDIO_PORT=$((54323 + PORT_OFFSET))
  SUPABASE_INBUCKET_PORT=$((54324 + PORT_OFFSET))
  SUPABASE_ANALYTICS_PORT=$((54327 + PORT_OFFSET))
  SUPABASE_POOLER_PORT=$((54329 + PORT_OFFSET))

  SUPABASE_WORKDIR="${STATE_DIR}/supabase-project"
  SUPABASE_CONFIG="${SUPABASE_WORKDIR}/supabase/config.toml"
  APP_ENV="${STATE_DIR}/app.env"
  METADATA_FILE="${STATE_DIR}/metadata.env"
  # Every isolated worktree uses the same intentionally local test accounts.
  # The database is isolated, so these identities cannot cross worktree
  # boundaries. Keep this list aligned with backend/src/worktree_seed.py.
  TEST_PASSWORD="Password123!"
  REGULAR_USER_EMAIL="regular-user@247ai.local"
  ORG_ADMIN_EMAIL="org-admin@247ai.local"
  PLATFORM_ADMIN_EMAIL="platform-admin@247ai.local"
  TEST_ORGANIZATION_NAME="24x7 AI Demo Studio"
  TEST_AGENT_ID="59252f36-255e-4e71-9250-c4ce3ac27eaa"
  TEST_APPOINTMENT_DEMO_SLUG="pleasant-pediatric-appointments"
  TEST_LEAD_DEMO_SLUG="copper-ridge-service-request"
  TEST_RESTAURANT_DEMO_SLUG="verdi-table-restaurant"
}

write_metadata() {
  mkdir -p "$STATE_DIR"
  chmod 700 "$STATE_DIR"
  cat > "$METADATA_FILE" <<EOF
WORKTREE_ID=$WORKTREE_ID
SUPABASE_PROJECT_ID=$SUPABASE_PROJECT_ID
APP_COMPOSE_PROJECT=$APP_COMPOSE_PROJECT
PORT_OFFSET=$PORT_OFFSET
SUPABASE_WORKDIR=$SUPABASE_WORKDIR
SUPABASE_CONFIG=$SUPABASE_CONFIG
APP_ENV=$APP_ENV
TEST_ORGANIZATION_NAME=$TEST_ORGANIZATION_NAME
TEST_AGENT_ID=$TEST_AGENT_ID
TEST_APPOINTMENT_DEMO_SLUG=$TEST_APPOINTMENT_DEMO_SLUG
TEST_LEAD_DEMO_SLUG=$TEST_LEAD_DEMO_SLUG
EOF
  chmod 600 "$METADATA_FILE"
}

render_supabase_config() {
  mkdir -p "${SUPABASE_WORKDIR}/supabase"
  python3 - "$ROOT/supabase/config.toml" "$SUPABASE_CONFIG" \
    "$SUPABASE_PROJECT_ID" "$SUPABASE_API_PORT" "$SUPABASE_DB_PORT" \
    "$SUPABASE_SHADOW_PORT" "$SUPABASE_POOLER_PORT" "$SUPABASE_STUDIO_PORT" \
    "$SUPABASE_INBUCKET_PORT" "$SUPABASE_ANALYTICS_PORT" "$APP_FRONTEND_PORT" <<'PY'
from pathlib import Path
import sys

source = Path(sys.argv[1])
target = Path(sys.argv[2])
project_id, api, db, shadow, pooler, studio, inbucket, analytics, frontend = sys.argv[3:]

ports = {
    ("api", "port"): api,
    ("db", "port"): db,
    ("db", "shadow_port"): shadow,
    ("db.pooler", "port"): pooler,
    ("studio", "port"): studio,
    ("inbucket", "port"): inbucket,
    ("analytics", "port"): analytics,
}
disabled_worktree_services = {"studio", "inbucket", "edge_runtime", "analytics"}

lines = []
section = ""
for raw in source.read_text(encoding="utf-8").splitlines():
    line = raw
    stripped = raw.strip()
    if stripped.startswith("[") and stripped.endswith("]"):
        section = stripped[1:-1]

    if "=" in stripped and not stripped.startswith("#"):
        key, _, _ = stripped.partition("=")
        key = key.strip()
        if (section, key) == ("", "project_id"):
            line = f'project_id = "{project_id}"'
        elif (section, key) in ports:
            line = f"{key} = {ports[(section, key)]}"
        elif section in disabled_worktree_services and key == "enabled":
            line = "enabled = false"
        elif section == "db.seed" and key == "enabled":
            line = "enabled = false"
        elif section in {"auth.external.google", "auth.external.linkedin_oidc"} and key == "enabled":
            line = "enabled = false"
        elif section == "auth" and key == "site_url":
            line = f'site_url = "http://localhost:{frontend}"'
        elif section == "auth" and key == "additional_redirect_urls":
            line = f'additional_redirect_urls = ["http://127.0.0.1:{frontend}"]'
    lines.append(line)

target.write_text("\n".join(lines) + "\n", encoding="utf-8")
PY
  chmod 600 "$SUPABASE_CONFIG"
}

prepare_app_env() {
  mkdir -p "$STATE_DIR"
  local source_env
  source_env="$(resolve_source_env)"
  local copied_source=false
  if [[ ! -f "$APP_ENV" ]]; then
    cp "$source_env" "$APP_ENV"
    chmod 600 "$APP_ENV"
    copied_source=true
  fi

  # Organization provider credentials are encrypted at rest. Keep each local
  # worktree on a stable generated key without ever generating keys for
  # staging or production environments.
  python3 "$ROOT/scripts/ensure-local-encryption-key.py" "$APP_ENV"

  # Provider credentials are intentionally refreshed on every setup. The
  # generated app.env persists between runs, while the canonical .env.local
  # may be created or rotated after the first worktree setup. Never replace a
  # previously valid key with a template placeholder.
  sync_voice_provider_settings "$source_env"

  if [[ "$COMMAND" == "up" ]]; then
    require_gemini_api_key "$source_env"
  fi

  ensure_local_encryption_key "$APP_ENV" "$copied_source"
  set_env_value "$APP_ENV" "ENV_FILE" "$APP_ENV"
  set_env_value "$APP_ENV" "ENVIRONMENT" "development"
  set_env_value "$APP_ENV" "DEBUG" "true"
  set_env_value "$APP_ENV" "PORT_OFFSET" "$PORT_OFFSET"
  set_env_value "$APP_ENV" "COMPOSE_PROJECT_SUFFIX" "$WORKTREE_ID"
  set_env_value "$APP_ENV" "HOST_FRONTEND_PORT" "$APP_FRONTEND_PORT"
  set_env_value "$APP_ENV" "HOST_BACKEND_PORT" "$APP_BACKEND_PORT"
  set_env_value "$APP_ENV" "HOST_VOICE_WS_PORT" "$APP_VOICE_WS_PORT"
  set_env_value "$APP_ENV" "HOST_OTEL_GRPC_PORT" "$OTEL_GRPC_PORT"
  set_env_value "$APP_ENV" "HOST_OTEL_HTTP_PORT" "$OTEL_HTTP_PORT"
  set_env_value "$APP_ENV" "HOST_OTEL_HEALTH_PORT" "$OTEL_HEALTH_PORT"
  set_env_value "$APP_ENV" "HOST_GRAFANA_PORT" "$GRAFANA_PORT"
  set_env_value "$APP_ENV" "HOST_PROMETHEUS_PORT" "$PROMETHEUS_PORT"
  set_env_value "$APP_ENV" "HOST_ALERTMANAGER_PORT" "$ALERTMANAGER_PORT"
  # Worktrees are the opt-in local telemetry test environment. The canonical
  # .env.local/.env.staging examples keep application telemetry disabled.
  set_env_value "$APP_ENV" "OTEL_ENABLED" "true"
  set_env_value "$APP_ENV" "OTEL_SERVICE_VERSION" "development"
  set_env_value "$APP_ENV" "OTEL_TRACES_SAMPLER_ARG" "1.0"
  set_env_value "$APP_ENV" "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT" "http://otel-collector:4318/v1/traces"
  set_env_value "$APP_ENV" "OTEL_EXPORTER_OTLP_TRACES_PROTOCOL" "http/protobuf"
  set_env_value "$APP_ENV" "OTEL_EXPORTER_OTLP_TRACES_HEADERS" ""
  set_env_value "$APP_ENV" "OTEL_EXPORTER_OTLP_METRICS_ENDPOINT" "http://otel-collector:4318/v1/metrics"
  set_env_value "$APP_ENV" "OTEL_EXPORTER_OTLP_METRICS_PROTOCOL" "http/protobuf"
  set_env_value "$APP_ENV" "OTEL_EXPORTER_OTLP_METRICS_HEADERS" ""
  set_env_value "$APP_ENV" "OTEL_EXPORTER_OTLP_LOGS_ENDPOINT" "http://otel-collector:4318/v1/logs"
  set_env_value "$APP_ENV" "OTEL_EXPORTER_OTLP_LOGS_PROTOCOL" "http/protobuf"
  set_env_value "$APP_ENV" "OTEL_EXPORTER_OTLP_LOGS_HEADERS" ""
  if is_placeholder_env_value "$(read_env_value "$APP_ENV" "GRAFANA_ADMIN_PASSWORD")"; then
    set_env_value "$APP_ENV" "GRAFANA_ADMIN_PASSWORD" "$(openssl rand -hex 24)"
  fi
  set_env_value "$APP_ENV" "APP_BASE_URL" "http://localhost:${APP_FRONTEND_PORT}"
  set_env_value "$APP_ENV" "API_BASE_URL" "http://localhost:${APP_BACKEND_PORT}"
  set_env_value "$APP_ENV" "NEXT_PUBLIC_API_URL" "http://localhost:${APP_BACKEND_PORT}"
  set_env_value "$APP_ENV" "VOICE_WS_PUBLIC_URL" "ws://localhost:${APP_VOICE_WS_PORT}"
  set_env_value "$APP_ENV" "GOOGLE_OAUTH_TOOL_REDIRECT_URI" "http://localhost:${APP_BACKEND_PORT}/api/v1/tools/callback"
  set_env_value "$APP_ENV" "MCP_OAUTH_REDIRECT_URI" "http://localhost:${APP_BACKEND_PORT}/api/v1/tools/callback"
  set_env_value "$APP_ENV" "CORS_ORIGINS" "[\"http://localhost:${APP_FRONTEND_PORT}\",\"http://127.0.0.1:${APP_FRONTEND_PORT}\",\"http://frontend:3000\",\"http://frontend-dev:3000\"]"
  set_env_value "$APP_ENV" "NEXT_PUBLIC_OTEL_ENABLED" "false"
  set_env_value "$APP_ENV" "NEXT_PUBLIC_OTEL_EXPORTER_OTLP_TRACES_ENDPOINT" "http://localhost:${OTEL_HTTP_PORT}/v1/traces"
  set_env_value "$APP_ENV" "NEXT_PUBLIC_OTEL_EXPORTER_OTLP_METRICS_ENDPOINT" "http://localhost:${OTEL_HTTP_PORT}/v1/metrics"
  set_env_value "$APP_ENV" "NEXT_PUBLIC_OTEL_EXPORTER_OTLP_LOGS_ENDPOINT" "http://localhost:${OTEL_HTTP_PORT}/v1/logs"
  set_env_value "$APP_ENV" "MCP_ALLOW_LOCAL_URLS" "true"

  # Isolated worktrees are local test environments. Keep opted-in call
  # recordings on the worktree filesystem so manual call-history testing does
  # not depend on R2 credentials or shared remote storage. The general local
  # environment example remains disabled by default for privacy.
  set_env_value "$APP_ENV" "VOICE_RECORDING_ENABLED" "true"
  set_env_value "$APP_ENV" "VOICE_RECORDING_TEE" "false"
  set_env_value "$APP_ENV" "RECORDING_STORAGE_BACKEND" "local"
  set_env_value "$APP_ENV" "RECORDING_STORAGE_LOCAL_ROOT" ".local-data/call-recordings"

  # Supabase status values are added by sync_supabase_credentials after the
  # local project starts. Keep source-env values during config-only generation.
  set_env_value "$APP_ENV" "SUPABASE_URL" "http://host.docker.internal:${SUPABASE_API_PORT}"
  set_env_value "$APP_ENV" "NEXT_PUBLIC_SUPABASE_URL" "http://127.0.0.1:${SUPABASE_API_PORT}"
  set_env_value "$APP_ENV" "DATABASE_URL" "postgresql://postgres:postgres@host.docker.internal:${SUPABASE_DB_PORT}/postgres"
}

validate_voice_provider_settings() {
  local gemini_key
  gemini_key="$(read_env_value "$APP_ENV" "GEMINI_API_KEY")"
  if is_placeholder_env_value "$gemini_key"; then
    die "GEMINI_API_KEY is not configured for this worktree; set it in the main checkout's .env.local or pass --source-env PATH"
  fi
}

supabase_status_env() {
  "$SUPABASE_CLI" --workdir "$SUPABASE_WORKDIR" status -o env 2>/dev/null
}

status_value() {
  local status_output="$1"
  local key="$2"
  local value
  value="$(printf '%s\n' "$status_output" | awk -F= -v name="$key" '$1 == name {
    sub(/^[^=]*=/, "")
    print
    exit
  }')"
  value="${value#\"}"
  value="${value%\"}"
  value="${value#\'}"
  value="${value%\'}"
  printf '%s' "$value"
}

sync_supabase_credentials() {
  local status_output="$1"
  local anon_key service_key jwt_secret
  anon_key="$(status_value "$status_output" ANON_KEY)"
  service_key="$(status_value "$status_output" SERVICE_ROLE_KEY)"
  jwt_secret="$(status_value "$status_output" JWT_SECRET)"
  [[ -n "$anon_key" && -n "$service_key" && -n "$jwt_secret" ]] || die "Supabase status did not return local credentials"

  set_env_value "$APP_ENV" "SUPABASE_URL" "http://host.docker.internal:${SUPABASE_API_PORT}"
  set_env_value "$APP_ENV" "SUPABASE_SERVICE_KEY" "$service_key"
  set_env_value "$APP_ENV" "SUPABASE_ANON_KEY" "$anon_key"
  set_env_value "$APP_ENV" "NEXT_PUBLIC_SUPABASE_URL" "http://127.0.0.1:${SUPABASE_API_PORT}"
  set_env_value "$APP_ENV" "NEXT_PUBLIC_SUPABASE_ANON_KEY" "$anon_key"
  set_env_value "$APP_ENV" "DATABASE_URL" "postgresql://postgres:postgres@host.docker.internal:${SUPABASE_DB_PORT}/postgres"
  set_env_value "$APP_ENV" "JWT_SECRET_KEY" "$jwt_secret"
}

require_supabase_cli() {
  command -v "$SUPABASE_CLI" >/dev/null 2>&1 || die "Supabase CLI not found. Install it before running a worktree stack."
}

require_docker() {
  command -v docker >/dev/null 2>&1 || die "Docker is required to run a worktree stack"
  docker compose version >/dev/null 2>&1 || die "Docker Compose is required to run a worktree stack"
}

compose() {
  docker compose \
    --project-directory "$ROOT" \
    --env-file "$APP_ENV" \
    --project-name "$APP_COMPOSE_PROJECT" \
    -f "$ROOT/docker-compose.dev.yml" \
    -f "$ROOT/docker-compose.observability.yml" "$@"
}

ensure_port_is_free() {
  local port="$1"
  if command -v lsof >/dev/null 2>&1 && lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
    die "port ${port} is already in use; choose another --port-offset"
  fi
}

check_ports() {
  local port
  if ! compose ps --status running -q backend-dev 2>/dev/null | grep -q .; then
    for port in \
      "$APP_FRONTEND_PORT" "$APP_BACKEND_PORT" "$APP_VOICE_WS_PORT" \
      "$OTEL_GRPC_PORT" "$OTEL_HTTP_PORT" "$OTEL_HEALTH_PORT" \
      "$GRAFANA_PORT" "$PROMETHEUS_PORT" "$ALERTMANAGER_PORT"; do
      ensure_port_is_free "$port"
    done
  fi

  if ! supabase_status_env >/dev/null 2>&1; then
    for port in \
      "$SUPABASE_SHADOW_PORT" "$SUPABASE_API_PORT" "$SUPABASE_DB_PORT" \
      "$SUPABASE_STUDIO_PORT" "$SUPABASE_INBUCKET_PORT" \
      "$SUPABASE_ANALYTICS_PORT" "$SUPABASE_POOLER_PORT"; do
      ensure_port_is_free "$port"
    done
  fi
}

start_supabase() {
  require_supabase_cli
  mkdir -p "$STATE_DIR"
  local start_log="${STATE_DIR}/supabase-start.log"
  if ! supabase_status_env >/dev/null 2>&1; then
    echo -e "${BLUE}Starting isolated Supabase project ${SUPABASE_PROJECT_ID}...${NC}"
    if ! "$SUPABASE_CLI" --workdir "$SUPABASE_WORKDIR" start >"$start_log" 2>&1; then
      chmod 600 "$start_log"
      echo "Supabase failed to start. Diagnostic output is in $start_log" >&2
      exit 1
    fi
    chmod 600 "$start_log"
  fi
  local status_output
  status_output="$(supabase_status_env)" || die "Supabase project is not running"
  sync_supabase_credentials "$status_output"
}

run_migrations() {
  echo -e "${BLUE}Applying Alembic migrations to the isolated database...${NC}"
  compose run --rm --no-deps --build backend-dev alembic upgrade head
}

run_master_data_seed() {
  if [[ "$SKIP_MASTER_DATA" == true ]]; then
    echo -e "${YELLOW}Skipping master-data synchronization (--skip-master-data).${NC}"
    return 0
  fi
  echo -e "${BLUE}Seeding code-owned platform data...${NC}"
  compose run --rm --no-deps --build backend-dev sh -lc \
    'set -euo pipefail; python -m src.master_data.cli preview --format json --output /tmp/worktree-master-data-plan.json; python -m src.master_data.cli apply --plan /tmp/worktree-master-data-plan.json'
}

run_worktree_seed() {
  echo -e "${BLUE}Creating standard email/password test accounts and local demo fixture...${NC}"
  compose run --rm --no-deps --build \
    --env "WORKTREE_ID=${WORKTREE_ID}" \
    backend-dev python scripts/worktree_seed.py
}

start_application() {
  echo -e "${BLUE}Starting isolated application Compose project ${APP_COMPOSE_PROJECT}...${NC}"
  compose up -d --build --remove-orphans
  if command -v curl >/dev/null 2>&1; then
    local attempt
    for attempt in $(seq 1 60); do
      if curl -fsS "http://127.0.0.1:${APP_BACKEND_PORT}/health" >/dev/null 2>&1; then
        return 0
      fi
      sleep 2
    done
    echo -e "${YELLOW}Backend did not become healthy within 120 seconds.${NC}" >&2
    compose ps >&2 || true
    return 1
  fi
}

show_config() {
  echo "Worktree: $WORKTREE_ID"
  echo "State directory: $STATE_DIR"
  echo "Supabase project: $SUPABASE_PROJECT_ID"
  echo "Port offset: $PORT_OFFSET"
  echo "Supabase API port: $SUPABASE_API_PORT"
  echo "Supabase DB port: $SUPABASE_DB_PORT"
  echo "Supabase Studio: disabled (lightweight worktree profile)"
  echo "Frontend host port: $APP_FRONTEND_PORT"
  echo "Backend host port: $APP_BACKEND_PORT"
  echo "Voice WebSocket host port: $APP_VOICE_WS_PORT"
  echo "App Compose project: $APP_COMPOSE_PROJECT"
  echo "App env: $APP_ENV"
  echo "Grafana: http://localhost:${GRAFANA_PORT} (admin password in app env)"
  echo "Prometheus: http://localhost:${PROMETHEUS_PORT}"
  echo "Alertmanager: http://localhost:${ALERTMANAGER_PORT}"
  local gemini_key
  gemini_key="$(read_env_value "$APP_ENV" "GEMINI_API_KEY")"
  if is_placeholder_env_value "$gemini_key"; then
    echo "Gemini API key: not configured"
  else
    echo "Gemini API key: configured"
  fi
  echo "Supabase config: $SUPABASE_CONFIG"
  show_test_accounts
}

show_test_accounts() {
  echo "Test organization: ${TEST_ORGANIZATION_NAME}"
  echo "Test agent ID: ${TEST_AGENT_ID}"
  echo "Demo URLs:"
  echo "  appointment: http://localhost:${APP_FRONTEND_PORT}/demo/${TEST_APPOINTMENT_DEMO_SLUG}"
  echo "  lead capture: http://localhost:${APP_FRONTEND_PORT}/demo/${TEST_LEAD_DEMO_SLUG}"
  echo "  restaurant: http://localhost:${APP_FRONTEND_PORT}/demo/${TEST_RESTAURANT_DEMO_SLUG}"
  echo "Test accounts (all use password ${TEST_PASSWORD}):"
  echo "  regular user: ${REGULAR_USER_EMAIL}"
  echo "  org admin: ${ORG_ADMIN_EMAIL}"
  echo "  platform admin: ${PLATFORM_ADMIN_EMAIL}"
}

show_status() {
  require_supabase_cli
  require_docker
  if [[ ! -f "$METADATA_FILE" || ! -f "$APP_ENV" ]]; then
    die "this worktree has not been configured; run '$0 config' first"
  fi
  echo "== Supabase status (safe endpoints only) =="
  local status_output
  if status_output="$(supabase_status_env)"; then
    echo "API URL: http://127.0.0.1:${SUPABASE_API_PORT}"
    echo "DB URL: postgresql://postgres:postgres@127.0.0.1:${SUPABASE_DB_PORT}/postgres"
    echo "Project: $SUPABASE_PROJECT_ID"
  else
    echo "Supabase: stopped"
  fi
  echo "== Application status =="
  compose ps
  echo "Frontend: http://localhost:${APP_FRONTEND_PORT}"
  echo "Backend: http://localhost:${APP_BACKEND_PORT}"
  echo "Voice WebSocket: ws://localhost:${APP_VOICE_WS_PORT}"
  show_test_accounts
}

stop_stack() {
  require_supabase_cli
  require_docker
  if [[ -f "$APP_ENV" ]]; then
    compose down
  fi
  if supabase_status_env >/dev/null 2>&1; then
    echo -e "${BLUE}Stopping Supabase project while preserving its data...${NC}"
    "$SUPABASE_CLI" --workdir "$SUPABASE_WORKDIR" stop
  fi
  echo -e "${GREEN}Worktree stack stopped. Data volumes were preserved.${NC}"
}

assert_safe_purge_target() {
  [[ "$STATE_DIR" != "/" && "$STATE_DIR" != "$ROOT" ]] \
    || die "refusing to purge a broad path: $STATE_DIR"
  [[ -f "$METADATA_FILE" ]] \
    || die "refusing to purge unrecognized state; expected $METADATA_FILE"
  local recorded_worktree
  recorded_worktree="$(read_env_value "$METADATA_FILE" WORKTREE_ID)"
  [[ "$recorded_worktree" == "$WORKTREE_ID" ]] \
    || die "state metadata does not belong to worktree $WORKTREE_ID"
}

purge_stack() {
  [[ "$CONFIRM_PURGE" == true ]] || die "purge is destructive; repeat with --yes"
  assert_safe_purge_target
  require_supabase_cli
  require_docker
  if [[ -f "$APP_ENV" ]]; then
    compose down
  fi
  if [[ -d "$SUPABASE_WORKDIR" ]]; then
    "$SUPABASE_CLI" --workdir "$SUPABASE_WORKDIR" stop --no-backup --project-id "$SUPABASE_PROJECT_ID" >/dev/null 2>&1 || true
  fi
  rm -rf "$STATE_DIR"
  echo -e "${GREEN}Removed only this worktree's application and Supabase state.${NC}"
}

up_stack() {
  require_supabase_cli
  require_docker
  render_supabase_config
  prepare_app_env
  validate_voice_provider_settings
  write_metadata
  check_ports
  start_supabase
  run_migrations
  run_master_data_seed
  run_worktree_seed
  start_application
  echo ""
  echo -e "${GREEN}Worktree stack is ready.${NC}"
  show_config
  echo "Frontend: http://localhost:${APP_FRONTEND_PORT}"
  echo "Backend: http://localhost:${APP_BACKEND_PORT}"
  echo "Supabase Studio: disabled (lightweight worktree profile)"
  show_test_accounts
}

main() {
  parse_args "$@"
  derive_identity

  case "$COMMAND" in
    help|--help|-h)
      usage
      ;;
    config)
      render_supabase_config
      prepare_app_env
      write_metadata
      show_config
      ;;
    up)
      up_stack
      ;;
    status)
      show_status
      ;;
    down)
      stop_stack
      ;;
    purge)
      purge_stack
      ;;
    *)
      die "unknown command '$COMMAND' (use '$0 help')"
      ;;
  esac
}

main "$@"
