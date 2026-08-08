#!/usr/bin/env bash
# Run Alembic migrations against a cloud Supabase database.
#
# Usage:
#   ENV_FILE=.env.staging REVISION=head ./scripts/deploy/run-alembic.sh
#   ENV_FILE=.env.cloud  REVISION=20260807000001 ./scripts/deploy/run-alembic.sh
#
# REVISION defaults to "head". Requires DATABASE_URL in the env file.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${ENV_FILE:-${ROOT}/.env.cloud}"
REVISION="${REVISION:-head}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing $ENV_FILE" >&2
  exit 1
fi

export DATABASE_URL
DATABASE_URL="$(python3 "${ROOT}/scripts/deploy/read-env-cloud.py" "$ENV_FILE" DATABASE_URL)"

export PYTHONPATH="${ROOT}:${PYTHONPATH:-}"

cd "${ROOT}/backend"
echo "Running alembic upgrade ${REVISION} (DATABASE_URL from $(basename "$ENV_FILE"))..."
alembic upgrade "${REVISION}"
echo "Migrations complete."
