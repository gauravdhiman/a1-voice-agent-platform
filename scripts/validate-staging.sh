#!/usr/bin/env bash
# Validate the current checkout against the shared cloud staging Supabase.
#
# Application runs LOCALLY (frontend, backend, voice-ws via docker-compose.dev.yml)
# but the database is the cloud staging project gdzwiwukcwbqohfwxxrx.
#
# This is the replacement for the former GitHub Actions auto-deploy to staging.
# Run it after merging to main and before manual production promotion.
#
# Usage:
#   ./scripts/validate-staging.sh              # migrate + sync release data + restart local staging stack
#   ./scripts/validate-staging.sh --no-start   # migrate + verify only (no Docker)
#   ./scripts/validate-staging.sh --migrate-only
#   ./scripts/validate-staging.sh --help
#
# Prerequisites:
#   - .env.staging at repo root (copy from .env.staging.example, filled with
#     staging Supabase service key + DATABASE_URL pooler URI)
#   - backend venv with alembic (uv pip install -r backend/requirements-dev.txt)
#   - Docker running (for --start flows)
#
# See docs/05_operations/staging_environment.md and
# docs/05_operations/deployment/worktree-and-release-strategy.md

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ENV_FILE:-${ROOT}/.env.staging}"
DO_MIGRATE=true
DO_VERIFY=true
DO_START=true
DO_HEALTH=true
HEALTH_TIMEOUT=90

usage() {
  sed -n '2,20p' "$0" | sed 's/^# //; s/^#//'
  echo ""
  echo "Flags:"
  echo "  --migrate-only   Only run compatibility check + migrate + verify (skip Docker)"
  echo "  --no-start       Same as --migrate-only"
  echo "  --no-health      Start stack but skip health polling"
  echo "  --env-file PATH  Env file (default: .env.staging)"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --migrate-only|--no-start) DO_START=false; DO_HEALTH=false; shift ;;
    --no-health) DO_HEALTH=false; shift ;;
    --env-file) ENV_FILE="$2"; shift 2 ;;
    --env-file=*) ENV_FILE="${1#*=}"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage; exit 1 ;;
  esac
done

if [[ "$ENV_FILE" != /* ]]; then
  ENV_FILE="${ROOT}/${ENV_FILE}"
fi
export ENV_FILE

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing $ENV_FILE" >&2
  echo "Copy .env.staging.example -> .env.staging and fill in:" >&2
  echo "  SUPABASE_SERVICE_KEY, DATABASE_URL (pooler), etc." >&2
  echo "See docs/05_operations/staging_environment.md" >&2
  exit 1
fi

echo "==> Staging validation"
echo "    Checkout: $(git -C "$ROOT" rev-parse --short HEAD) ($(git -C "$ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null || echo detached))"
echo "    Env file: $(basename "$ENV_FILE")"
python3 "${ROOT}/scripts/deploy/read-env-cloud.py" "$ENV_FILE" SUPABASE_URL 2>/dev/null | sed 's/^/    Supabase: /' || true
echo ""

# 1. Compatibility check (read-only, safe for shared staging)
echo "==> [1/5] Checking Alembic compatibility against staging..."
python3 "${ROOT}/scripts/deploy/check_alembic_compatibility.py" --env-file "$ENV_FILE"
echo "    Compatibility OK"
echo ""

# 2. Migrate
if [[ "$DO_MIGRATE" == "true" ]]; then
  echo "==> [2/5] Running staging migrations (upgrade head)..."
  chmod +x "${ROOT}/scripts/deploy.sh" "${ROOT}/scripts/deploy/run-alembic.sh" "${ROOT}/scripts/deploy/run-alembic-cloud.sh"
  "${ROOT}/scripts/deploy.sh" migrate --env-file "$ENV_FILE"
  echo ""
fi

# 3. Verify phone-number backfill postconditions
if [[ "$DO_VERIFY" == "true" ]]; then
  echo "==> [3/5] Verifying phone-number data migration..."
  python3 "${ROOT}/scripts/deploy/verify_phone_number_backfill.py" --env-file "$ENV_FILE"
  python3 "${ROOT}/scripts/deploy/verify_data_api_security.py" --env-file "$ENV_FILE"
  echo ""
fi

# 4. Materialize the code-owned system-pricing meters, native tools, and public
#    demo fixture from this release. Existing usage rates are preserved; the
#    sync adds missing meters without resetting admin-managed rates. The demo
#    sync is explicit and idempotent; it does not create local test accounts or
#    grant staging credits.
if [[ "$DO_START" == "true" ]]; then
  echo "==> [4/5] Synchronizing system pricing, native tools, and public demos in staging..."
  COMPOSE_PROJECT_NAME=247ai-staging \
    ENV_FILE="$ENV_FILE" \
    "${ROOT}/scripts/deploy/sync-release-fixtures.sh" \
    --env-file "$ENV_FILE" \
    --project-name 247ai-staging
  echo ""
else
  echo "==> [4/5] Skipped release-data synchronization (--migrate-only)."
fi

# 5. Start local stack against staging (--env staging)
if [[ "$DO_START" == "true" ]]; then
  echo "==> [5/5] Starting local application stack against staging..."
  echo "    Command: ./start.sh start dev --env staging"
  "${ROOT}/start.sh" start dev --env staging
  echo ""
  if [[ "$DO_HEALTH" == "true" ]]; then
    echo "    Waiting for health endpoints (timeout ${HEALTH_TIMEOUT}s)..."
    deadline=$(( $(date +%s) + HEALTH_TIMEOUT ))
    backend_ok=false
    voice_ok=false
    # Resolve ports from env or defaults (HOST_*_PORT)
    backend_port="$(python3 "${ROOT}/scripts/deploy/read-env-cloud.py" "$ENV_FILE" HOST_BACKEND_PORT 2>/dev/null || echo 8000)"
    voice_port="$(python3 "${ROOT}/scripts/deploy/read-env-cloud.py" "$ENV_FILE" HOST_VOICE_WS_PORT 2>/dev/null || echo 7860)"
    # Fall back if empty
    [[ -n "$backend_port" ]] || backend_port=8000
    [[ -n "$voice_port" ]] || voice_port=7860
    while (( $(date +%s) < deadline )); do
      if curl -fsS "http://localhost:${backend_port}/health" >/dev/null 2>&1; then backend_ok=true; fi
      if curl -fsS "http://localhost:${voice_port}/health" >/dev/null 2>&1; then voice_ok=true; fi
      if [[ "$backend_ok" == "true" && "$voice_ok" == "true" ]]; then break; fi
      sleep 2
    done
    echo "    Backend http://localhost:${backend_port}/health: $([ "$backend_ok" = true ] && echo OK || echo 'not ready yet')"
    echo "    voice-ws http://localhost:${voice_port}/health: $([ "$voice_ok" = true ] && echo OK || echo 'not ready yet')"
    if [[ "$backend_ok" != "true" ]]; then
      echo "    Backend not healthy — check: ./start.sh logs dev" >&2
    fi
    echo ""
    echo "    Open http://localhost:3000 — auth + data are from staging Supabase."
    echo "    Run browser + PSTN smoke tests with a release-test org that has"
    echo "    active voice entitlements and prepaid credit headroom (see"
    echo "    docs/05_operations/deployment/runbook.md#mandatory-release-gate-ai-agent-calling)."
  fi
else
  echo "==> [5/5] Skipped release sync and Docker start (--migrate-only)."
  echo "    Before staging app startup, rerun ./scripts/validate-staging.sh"
  echo "    to synchronize this release's system pricing, tools, and demos."
fi

echo ""
echo "==> Staging validation complete."
echo "    Next: manual smoke tests, then Promote to production with the tested SHA:"
echo "    Actions -> Promote to production -> ref = $(git -C "$ROOT" rev-parse HEAD)"
