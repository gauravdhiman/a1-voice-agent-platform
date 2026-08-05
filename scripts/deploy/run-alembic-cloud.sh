#!/usr/bin/env bash
# Run Alembic migrations against the database in .env.cloud (production Supabase).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${ENV_FILE:-${ROOT}/.env.cloud}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing $ENV_FILE" >&2
  exit 1
fi

export DATABASE_URL
DATABASE_URL="$(python3 "${ROOT}/scripts/deploy/read-env-cloud.py" "$ENV_FILE" DATABASE_URL)"

export PYTHONPATH="${ROOT}:${PYTHONPATH:-}"

cd "${ROOT}/backend"
echo "Running alembic upgrade head (DATABASE_URL from $(basename "$ENV_FILE"))..."
alembic upgrade head
echo "Migrations complete."
