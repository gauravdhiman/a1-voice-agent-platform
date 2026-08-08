#!/usr/bin/env bash
# Run Alembic migrations against the database in .env.cloud (production Supabase).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
export ENV_FILE="${ENV_FILE:-${ROOT}/.env.cloud}"
export REVISION="${REVISION:-head}"
exec "${ROOT}/scripts/deploy/run-alembic.sh"
