#!/usr/bin/env bash
# Validate the repository-wide contract for canonical environment files.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

assert_contains() {
  local file="$1"
  local expected="$2"
  if ! grep -Fq -- "$expected" "$file"; then
    echo "Expected $file to contain: $expected" >&2
    exit 1
  fi
}

assert_not_contains() {
  local file="$1"
  local unexpected="$2"
  if grep -Fq -- "$unexpected" "$file"; then
    echo "Expected $file not to contain: $unexpected" >&2
    exit 1
  fi
}

for file in .env.local.example .env.staging.example .env.prod.example; do
  [[ -f "$ROOT/$file" ]] || { echo "Missing template: $file" >&2; exit 1; }
done

for legacy in .env .env.cloud .env.cloud.example .env.dev; do
  [[ ! -e "$ROOT/$legacy" ]] || { echo "Legacy file exists: $legacy" >&2; exit 1; }
done

template_keys() {
  awk -F= '/^[A-Za-z_][A-Za-z0-9_]*=/{ print $1 }' "$1" | sort
}

for file in .env.local.example .env.staging.example .env.prod.example; do
  duplicate_keys="$(template_keys "$ROOT/$file" | uniq -d)"
  if [[ -n "$duplicate_keys" ]]; then
    echo "Duplicate keys in $file: $duplicate_keys" >&2
    exit 1
  fi
done

diff -u \
  <(template_keys "$ROOT/.env.local.example") \
  <(template_keys "$ROOT/.env.staging.example")
diff -u \
  <(template_keys "$ROOT/.env.local.example") \
  <(template_keys "$ROOT/.env.prod.example")

assert_contains "$ROOT/start.sh" 'ENV_FILE="$PROJECT_DIR/.env.local"'
assert_contains "$ROOT/start.sh" 'ENV_FILE="$PROJECT_DIR/.env.staging"'
assert_contains "$ROOT/start.sh" 'ENV_FILE="$PROJECT_DIR/.env.prod"'
assert_contains "$ROOT/start.sh" 'run_startup_migrations'
assert_contains "$ROOT/start.sh" 'alembic upgrade head'
assert_contains "$ROOT/start.sh" 'compose "$COMPOSE_FILE_DEV" up -d --build'
assert_contains "$ROOT/start.sh" 'compose "$COMPOSE_FILE_PROD" up -d --build'
assert_contains "$ROOT/docker-compose.dev.yml" '${ENV_FILE:-.env.local}'
assert_contains "$ROOT/docker-compose.yml" '${ENV_FILE:-.env.prod}'
assert_contains "$ROOT/scripts/deploy.sh" '${ROOT}/.env.prod'
assert_contains "$ROOT/scripts/deploy/gcp-deploy.sh" 'gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet'
assert_contains "$ROOT/scripts/deploy/gcp-deploy.sh" 'RELEASE_TAG="${RELEASE_TAG:-latest}"'
assert_contains "$ROOT/scripts/deploy/gcp-deploy.sh" 'BACKEND_IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/backend:${RELEASE_TAG}"'
assert_not_contains "$ROOT/scripts/deploy/gcp-deploy.sh" '--allow-unauthenticated'
assert_contains "$ROOT/scripts/deploy/oci-deploy-voice-ws.sh" 'SSH_KEY="${HOME}/${SSH_KEY#\~/}"'

if RELEASE_TAG='not a valid tag' bash "$ROOT/scripts/deploy/gcp-deploy.sh" >/dev/null 2>&1; then
  echo "Expected an invalid release tag to fail before deployment" >&2
  exit 1
fi

for compose_file in docker-compose.dev.yml docker-compose.yml; do
  assert_contains "$ROOT/$compose_file" 'VOICE_RECORDING_ENABLED=${VOICE_RECORDING_ENABLED:-false}'
  assert_contains "$ROOT/$compose_file" 'RECORDING_STORAGE_BACKEND=${RECORDING_STORAGE_BACKEND:-local}'
  assert_contains "$ROOT/$compose_file" 'RECORDING_R2_ENDPOINT=${RECORDING_R2_ENDPOINT:-}'
  assert_contains "$ROOT/$compose_file" 'RECORDING_R2_BUCKET=${RECORDING_R2_BUCKET:-}'
  assert_contains "$ROOT/$compose_file" 'RECORDING_R2_ACCESS_KEY_ID=${RECORDING_R2_ACCESS_KEY_ID:-}'
  assert_contains "$ROOT/$compose_file" 'RECORDING_R2_SECRET_ACCESS_KEY=${RECORDING_R2_SECRET_ACCESS_KEY:-}'
  assert_contains "$ROOT/$compose_file" 'RECORDING_R2_PRESIGN_TTL_SECONDS=${RECORDING_R2_PRESIGN_TTL_SECONDS:-300}'
done

assert_contains "$ROOT/.env.staging.example" 'RECORDING_R2_ENDPOINT=https://e168c1bca6abb23e49bae87a6a8ea38b.r2.cloudflarestorage.com'
assert_contains "$ROOT/.env.staging.example" 'RECORDING_R2_BUCKET=247ai-call-recordings-staging'
assert_contains "$ROOT/.env.prod.example" 'RECORDING_R2_ENDPOINT=https://e168c1bca6abb23e49bae87a6a8ea38b.r2.cloudflarestorage.com'
assert_contains "$ROOT/.env.prod.example" 'RECORDING_R2_BUCKET=247ai-call-recordings-production'
assert_contains "$ROOT/voice-ws/requirements.txt" 'boto3>='
assert_contains "$ROOT/.github/workflows/migration-graph.yml" 'check_alembic_compatibility.py --repository-only'
assert_contains "$ROOT/.github/workflows/agent-evals.yml" 'check_alembic_compatibility.py --repository-only'

workflow="$ROOT/.github/workflows/deploy-cloud.yml"
production_workflow="$ROOT/.github/workflows/promote-production.yml"
migration_requirements="$ROOT/scripts/deploy/requirements-migrations.txt"
[[ -f "$migration_requirements" ]] || { echo "Missing migration requirements: $migration_requirements" >&2; exit 1; }
assert_contains "$migration_requirements" 'alembic==1.14.0'
assert_contains "$migration_requirements" 'psycopg2-binary==2.9.11'
assert_contains "$workflow" 'name: Deploy Cloud (staging)'
assert_contains "$workflow" 'group: deploy-staging'
assert_contains "$workflow" 'migrate-staging:'
assert_contains "$workflow" 'environment: staging'
assert_contains "$workflow" 'ENV_STAGING: ${{ secrets.ENV_STAGING }}'
assert_contains "$workflow" 'check_alembic_compatibility.py --env-file .env.staging'
assert_contains "$workflow" './scripts/deploy.sh migrate --env-file .env.staging'
assert_contains "$workflow" 'GCP_PROJECT_ID: ${{ vars.STAGING_GCP_PROJECT_ID }}'
assert_not_contains "$workflow" 'migrate-production:'
assert_not_contains "$workflow" 'secrets.ENV_PROD'
assert_not_contains "$workflow" 'if: ${{ secrets.OCI_SSH_KEY != '\'''\'' }}'
assert_contains "$workflow" 'id: check-oci-ssh'
assert_contains "$workflow" 'OCI_SSH_KEY: ${{ secrets.STAGING_OCI_SSH_KEY }}'
assert_contains "$workflow" 'if: steps.check-oci-ssh.outputs.configured == '\''true'\'''

[[ -f "$production_workflow" ]] || {
  echo "Missing manual production workflow: $production_workflow" >&2
  exit 1
}
assert_contains "$production_workflow" 'name: Promote to production'
assert_contains "$production_workflow" 'group: promote-production'
assert_contains "$production_workflow" 'workflow_dispatch:'
assert_contains "$production_workflow" 'PROMOTION_REF: ${{ inputs.ref }}'
assert_contains "$production_workflow" 'full 40-character commit SHA'
assert_contains "$production_workflow" 'ref: ${{ inputs.ref }}'
assert_contains "$production_workflow" 'environment: production'
assert_contains "$production_workflow" 'ENV_PROD: ${{ secrets.ENV_PROD }}'
assert_contains "$production_workflow" 'check_alembic_compatibility.py --env-file .env.prod'
assert_contains "$production_workflow" './scripts/deploy.sh migrate --env-file .env.prod'
assert_contains "$workflow" 'echo "RELEASE_TAG=$(git rev-parse HEAD)" >> "$GITHUB_ENV"'
assert_contains "$production_workflow" 'echo "RELEASE_TAG=$(git rev-parse HEAD)" >> "$GITHUB_ENV"'

# The startup guide must describe selection, never copy-to-.env switching.
assert_contains "$ROOT/README_STARTUP.md" './start.sh start dev --env staging'
assert_contains "$ROOT/README_STARTUP.md" './start.sh config --env staging'
assert_not_contains "$ROOT/README_STARTUP.md" 'cp .env.staging .env'
assert_not_contains "$ROOT/README_STARTUP.md" '| `.env` |'

echo "Environment contract tests passed."
