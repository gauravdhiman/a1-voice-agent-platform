#!/usr/bin/env bash
# Synchronize code-owned release data for a selected environment.
#
# This is an explicit bootstrap step, not an application-startup hook. It
# publishes the native tool catalog and the three public demo agents together so
# a release cannot expose demo pages whose required tools are missing.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${ENV_FILE:-${ROOT}/.env.staging}"
PROJECT_NAME="${COMPOSE_PROJECT_NAME:-247ai-staging}"
COMPOSE_FILE_PATH="${COMPOSE_FILE_PATH:-${ROOT}/docker-compose.dev.yml}"

usage() {
  sed -n '2,8p' "$0" | sed 's/^# \{0,1\}//'
  echo ""
  echo "Usage: $0 [--env-file PATH] [--project-name NAME] [--compose-file PATH]"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --env-file)
      [[ $# -ge 2 ]] || { echo "Missing value for --env-file" >&2; exit 1; }
      ENV_FILE="$2"
      shift 2
      ;;
    --env-file=*)
      ENV_FILE="${1#*=}"
      shift
      ;;
    --project-name)
      [[ $# -ge 2 ]] || { echo "Missing value for --project-name" >&2; exit 1; }
      PROJECT_NAME="$2"
      shift 2
      ;;
    --project-name=*)
      PROJECT_NAME="${1#*=}"
      shift
      ;;
    --compose-file)
      [[ $# -ge 2 ]] || { echo "Missing value for --compose-file" >&2; exit 1; }
      COMPOSE_FILE_PATH="$2"
      shift 2
      ;;
    --compose-file=*)
      COMPOSE_FILE_PATH="${1#*=}"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ "$ENV_FILE" != /* ]]; then
  ENV_FILE="${ROOT}/${ENV_FILE}"
fi
if [[ "$COMPOSE_FILE_PATH" != /* ]]; then
  COMPOSE_FILE_PATH="${ROOT}/${COMPOSE_FILE_PATH}"
fi

[[ -f "$ENV_FILE" ]] || { echo "Missing env file: $ENV_FILE" >&2; exit 1; }
[[ -f "$COMPOSE_FILE_PATH" ]] || {
  echo "Missing Compose file: $COMPOSE_FILE_PATH" >&2
  exit 1
}
command -v docker >/dev/null 2>&1 || {
  echo "Docker is required to synchronize release fixtures" >&2
  exit 1
}
docker compose version >/dev/null 2>&1 || {
  echo "Docker Compose is required to synchronize release fixtures" >&2
  exit 1
}

environment_name="$(
  python3 "${ROOT}/scripts/deploy/read-env-cloud.py" "$ENV_FILE" ENVIRONMENT \
    2>/dev/null || true
)"
environment_name="$(printf '%s' "$environment_name" | tr '[:upper:]' '[:lower:]')"
case "$environment_name" in
  development|staging|production) ;;
  *)
    echo "ENVIRONMENT in $(basename "$ENV_FILE") must be development, staging, or production" >&2
    exit 1
    ;;
esac

echo "Synchronizing release fixtures in ${environment_name} from $(basename "$ENV_FILE")..."

seed_command='set -eu
plan="$(mktemp)"
trap '\''rm -f "$plan"'\'' EXIT
python -m src.master_data.cli preview --domain platform_tools --format json --output "$plan" >/dev/null
python -m src.master_data.cli apply --plan "$plan"
python scripts/sync_demo_fixtures.py --allow-production'

ENV_FILE="$ENV_FILE" ENVIRONMENT="$environment_name" docker compose \
  --project-directory "$ROOT" \
  --env-file "$ENV_FILE" \
  --project-name "$PROJECT_NAME" \
  -f "$COMPOSE_FILE_PATH" \
  run --rm --no-deps --build backend-dev sh -c "$seed_command"

echo "Release fixtures synchronized."
