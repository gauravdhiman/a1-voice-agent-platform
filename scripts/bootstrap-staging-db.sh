#!/usr/bin/env bash
# Bootstrap the cloud staging Supabase project (gdzwiwukcwbqohfwxxrx).
#
# Brings schema current and seeds billing catalog so plan-version backfill works.
#
# Prerequisites:
#   1. Copy .env.staging.example → .env.staging and fill in:
#      - SUPABASE_SERVICE_KEY (Settings → API)
#      - DATABASE_URL password (Settings → Database, us-west-2 pooler)
#   2. Backend venv with alembic: cd backend && uv pip install -r requirements-dev.txt
#
# Usage:
#   ./scripts/bootstrap-staging-db.sh
#   ./scripts/bootstrap-staging-db.sh --skip-seed   # migrations only
#   ./scripts/bootstrap-staging-db.sh --dry-run-seed
#
# Order (important for plan_versions backfill):
#   1. alembic upgrade 20260807000001  (schema before entitlements)
#   2. stripe_manager seed             (subscription_plans + credits)
#   3. alembic upgrade head            (entitlements + backfill from subscription_plans)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ENV_FILE:-${ROOT}/.env.staging}"
SKIP_SEED=false
DRY_RUN_SEED=false

for arg in "$@"; do
  case "$arg" in
    --skip-seed) SKIP_SEED=true ;;
    --dry-run-seed) DRY_RUN_SEED=true ;;
    -h|--help)
      sed -n '2,20p' "$0"
      exit 0
      ;;
    *)
      echo "Unknown option: $arg" >&2
      exit 1
      ;;
  esac
done

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing $ENV_FILE — copy .env.staging.example and fill in staging credentials." >&2
  exit 1
fi

echo "==> Staging bootstrap using $(basename "$ENV_FILE")"
echo "    Project: gdzwiwukcwbqohfwxxrx (oc-dev-ai-voice-agent-platform)"
echo ""

echo "==> Step 1/3: Alembic upgrade to 20260807000001 (pre-entitlements)..."
ENV_FILE="$ENV_FILE" REVISION=20260807000001 "${ROOT}/scripts/deploy/run-alembic.sh"

if [[ "$SKIP_SEED" == "false" ]]; then
  echo ""
  echo "==> Step 2/3: Seed billing catalog from Stripe..."
  SEED_ARGS=(seed)
  if [[ "$DRY_RUN_SEED" == "true" ]]; then
    SEED_ARGS+=(--dry-run)
  fi
  export PYTHONPATH="${ROOT}:${PYTHONPATH:-}"

  # Export staging secrets safely (handles special chars; avoids brittle ``source``).
  staging_var() {
    local key="$1"
    if python3 "${ROOT}/scripts/deploy/read-env-cloud.py" "$ENV_FILE" "$key" >/dev/null 2>&1; then
      export "$key"="$(python3 "${ROOT}/scripts/deploy/read-env-cloud.py" "$ENV_FILE" "$key")"
    fi
  }
  for key in SUPABASE_URL SUPABASE_SERVICE_KEY SUPABASE_ANON_KEY STRIPE_SECRET_KEY; do
    staging_var "$key"
  done

  cd "${ROOT}/backend"
  python3 scripts/stripe_manager.py "${SEED_ARGS[@]}"
else
  echo ""
  echo "==> Step 2/3: Skipped (--skip-seed)"
fi

echo ""
echo "==> Step 3/3: Alembic upgrade head (entitlements + plan backfill)..."
ENV_FILE="$ENV_FILE" REVISION=head "${ROOT}/scripts/deploy/run-alembic.sh"

echo ""
echo "==> Staging bootstrap complete."
echo "    Verify: cp .env.staging .env && ./start.sh restart dev"
echo "    Docs:   docs/05_operations/staging_environment.md"
