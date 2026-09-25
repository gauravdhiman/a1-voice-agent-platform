#!/usr/bin/env bash
# Run Alembic migrations against a cloud Supabase database.
#
# Usage:
#   ENV_FILE=.env.staging REVISION=head ./scripts/deploy/run-alembic.sh
#   ENV_FILE=.env.prod  REVISION=20260807000001 ./scripts/deploy/run-alembic.sh
#
# REVISION defaults to "head". Requires DATABASE_URL in the env file.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${ENV_FILE:-${ROOT}/.env.prod}"
REVISION="${REVISION:-head}"

if [[ "$ENV_FILE" != /* ]]; then
  ENV_FILE="${ROOT}/${ENV_FILE}"
fi

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing $ENV_FILE" >&2
  exit 1
fi

export DATABASE_URL
DATABASE_URL="$(python3 "${ROOT}/scripts/deploy/read-env-cloud.py" "$ENV_FILE" DATABASE_URL)"

# Migrations that transform encrypted application data must use the same
# deployment keyring as the running services. Load only the values needed by
# migration code; never source the env file as shell code.
export ENVIRONMENT
ENVIRONMENT="$(python3 "${ROOT}/scripts/deploy/read-env-cloud.py" "$ENV_FILE" ENVIRONMENT || true)"
export ENCRYPTION_KEY
ENCRYPTION_KEY="$(python3 "${ROOT}/scripts/deploy/read-env-cloud.py" "$ENV_FILE" ENCRYPTION_KEY || true)"
export ENCRYPTION_KEY_FALLBACKS
ENCRYPTION_KEY_FALLBACKS="$(python3 "${ROOT}/scripts/deploy/read-env-cloud.py" "$ENV_FILE" ENCRYPTION_KEY_FALLBACKS || true)"

export PYTHONPATH="${ROOT}:${PYTHONPATH:-}"

echo "Checking Alembic migration compatibility (DATABASE_URL from $(basename "$ENV_FILE"))..."
python3 "${ROOT}/scripts/deploy/check_alembic_compatibility.py" \
  --env-file "$ENV_FILE"

cd "${ROOT}/backend"
echo "Running alembic upgrade ${REVISION} (DATABASE_URL from $(basename "$ENV_FILE"))..."
alembic upgrade "${REVISION}"
cd "$ROOT"

# Supabase PostgREST caches the exposed schema. Tell it to reload after a
# successful migration so a newly added column is immediately available to
# REST writes from the application.
python3 - <<'PY'
import os

from sqlalchemy import create_engine, text


engine = create_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)
try:
    with engine.begin() as connection:
        connection.execute(text("SELECT pg_notify('pgrst', 'reload schema')"))
finally:
    engine.dispose()
PY

echo "PostgREST schema cache reload requested."
echo "Migrations complete."
