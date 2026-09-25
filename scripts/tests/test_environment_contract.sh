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

assert_before() {
  local file="$1"
  local before="$2"
  local after="$3"
  local before_line after_line
  before_line="$(grep -nF -- "$before" "$file" | head -1 | cut -d: -f1 || true)"
  after_line="$(grep -nF -- "$after" "$file" | head -1 | cut -d: -f1 || true)"
  if [[ -z "$before_line" || -z "$after_line" || "$before_line" -ge "$after_line" ]]; then
    echo "Expected $file to run '$before' before '$after'" >&2
    exit 1
  fi
}

for file in .env.local.example .env.staging.example .env.prod.example; do
  [[ -f "$ROOT/$file" ]] || { echo "Missing template: $file" >&2; exit 1; }
done

for file in deploy/config/local.env deploy/config/staging.env deploy/config/production.env; do
  [[ -f "$ROOT/$file" ]] || { echo "Missing versioned config: $file" >&2; exit 1; }
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

for file in .env.local.example .env.staging.example .env.prod.example; do
  assert_contains "$ROOT/$file" 'SECRET_MANAGER_MODE='
  assert_contains "$ROOT/$file" 'GCP_SECRET_MANAGER_PROJECT_ID='
  assert_contains "$ROOT/$file" 'GCP_SECRET_NAME_PREFIX='
  assert_contains "$ROOT/$file" 'GCP_BACKEND_RUNTIME_SERVICE_ACCOUNT='
  assert_contains "$ROOT/$file" 'OCI_VAULT_ID='
  assert_contains "$ROOT/$file" 'OCI_SECRET_NAME_PREFIX='
  assert_contains "$ROOT/$file" 'NEXT_PUBLIC_POSTHOG_KEY='
  assert_contains "$ROOT/$file" 'NEXT_PUBLIC_POSTHOG_HOST=https://us.i.posthog.com'
done
assert_contains "$ROOT/frontend/.env.local.example" 'NEXT_PUBLIC_POSTHOG_KEY='
assert_contains "$ROOT/frontend/.env.local.example" 'NEXT_PUBLIC_POSTHOG_HOST=https://us.i.posthog.com'
assert_contains "$ROOT/frontend/.env.local.example" 'NEXT_PUBLIC_TURNSTILE_SITE_KEY='
assert_contains "$ROOT/docker-compose.dev.yml" 'NEXT_PUBLIC_POSTHOG_KEY=${NEXT_PUBLIC_POSTHOG_KEY:-}'
assert_contains "$ROOT/docker-compose.dev.yml" 'NEXT_PUBLIC_POSTHOG_HOST=${NEXT_PUBLIC_POSTHOG_HOST:-https://us.i.posthog.com}'
assert_contains "$ROOT/docker-compose.yml" 'NEXT_PUBLIC_POSTHOG_KEY=${NEXT_PUBLIC_POSTHOG_KEY:-}'
assert_contains "$ROOT/docker-compose.yml" 'NEXT_PUBLIC_POSTHOG_HOST=${NEXT_PUBLIC_POSTHOG_HOST:-https://us.i.posthog.com}'
assert_contains "$ROOT/frontend/Dockerfile" 'ARG NEXT_PUBLIC_POSTHOG_KEY'
assert_contains "$ROOT/frontend/Dockerfile" 'ARG NEXT_PUBLIC_POSTHOG_HOST'
assert_contains "$ROOT/frontend/Dockerfile" 'ARG NEXT_PUBLIC_TURNSTILE_SITE_KEY'
assert_contains "$ROOT/docker-compose.dev.yml" 'NEXT_PUBLIC_TURNSTILE_SITE_KEY=${NEXT_PUBLIC_TURNSTILE_SITE_KEY:-}'
assert_contains "$ROOT/docker-compose.yml" 'NEXT_PUBLIC_TURNSTILE_SITE_KEY=${NEXT_PUBLIC_TURNSTILE_SITE_KEY:-}'
assert_contains "$ROOT/scripts/deploy/gcp-deploy.sh" 'NEXT_PUBLIC_POSTHOG_KEY="$(read_env NEXT_PUBLIC_POSTHOG_KEY)"'
assert_contains "$ROOT/scripts/deploy/gcp-deploy.sh" '--build-arg "NEXT_PUBLIC_POSTHOG_KEY=${NEXT_PUBLIC_POSTHOG_KEY}"'
assert_contains "$ROOT/scripts/deploy/gcp-deploy.sh" '--build-arg "NEXT_PUBLIC_POSTHOG_HOST=${NEXT_PUBLIC_POSTHOG_HOST}"'
assert_contains "$ROOT/scripts/deploy/gcp-deploy.sh" '--build-arg "NEXT_PUBLIC_TURNSTILE_SITE_KEY=${NEXT_PUBLIC_TURNSTILE_SITE_KEY}"'
assert_contains "$ROOT/scripts/deploy/gcp-deploy.sh" '--build-arg "NEXT_PUBLIC_APP_DESCRIPTION=${NEXT_PUBLIC_APP_DESCRIPTION}"'

assert_contains "$ROOT/start.sh" 'ENV_FILE="$PROJECT_DIR/.env.local"'
assert_contains "$ROOT/start.sh" 'ENV_FILE="$PROJECT_DIR/.env.staging"'
assert_contains "$ROOT/start.sh" 'ENV_FILE="$PROJECT_DIR/.env.prod"'
assert_contains "$ROOT/start.sh" 'run_startup_migrations'
assert_contains "$ROOT/start.sh" 'alembic upgrade head'
assert_contains "$ROOT/start.sh" 'compose "$COMPOSE_FILE_DEV" up -d --build'
assert_contains "$ROOT/start.sh" 'compose "$COMPOSE_FILE_PROD" up -d --build'
assert_contains "$ROOT/scripts/validate-staging.sh" 'sync-release-fixtures.sh'
assert_contains "$ROOT/scripts/deploy/sync-native-tools.sh" 'preview --domain platform_tools'
assert_contains "$ROOT/scripts/deploy/sync-native-tools.sh" 'apply --plan'
[[ -x "$ROOT/scripts/deploy/sync-native-tools.sh" ]] || {
  echo "Native tool synchronization script is not executable" >&2
  exit 1
}
assert_contains "$ROOT/scripts/deploy/sync-native-tools.sh" 'docker compose'
assert_contains "$ROOT/scripts/deploy/sync-release-fixtures.sh" 'sync_demo_fixtures.py'
assert_contains "$ROOT/scripts/deploy/sync-release-fixtures.sh" 'preview --domain platform_tools'
assert_contains "$ROOT/scripts/deploy/sync-release-fixtures.sh" 'apply --plan'
[[ -x "$ROOT/scripts/deploy/sync-release-fixtures.sh" ]] || {
  echo "Release fixture synchronization script is not executable" >&2
  exit 1
}
assert_contains "$ROOT/docker-compose.dev.yml" '${ENV_FILE:-.env.local}'
assert_contains "$ROOT/docker-compose.yml" '${ENV_FILE:-.env.prod}'
assert_contains "$ROOT/scripts/deploy.sh" '${ROOT}/.env.prod'
assert_contains "$ROOT/scripts/validate-staging.sh" 'sync-release-fixtures.sh'
assert_contains "$ROOT/scripts/deploy/sync-native-tools.sh" 'preview --domain platform_tools'
assert_contains "$ROOT/scripts/deploy/sync-native-tools.sh" 'apply --plan'
[[ -x "$ROOT/scripts/deploy/sync-native-tools.sh" ]] || {
  echo "Native tool synchronization script is not executable" >&2
  exit 1
}
assert_contains "$ROOT/scripts/deploy/sync-native-tools.sh" 'docker compose'
assert_contains "$ROOT/scripts/deploy/gcp-deploy.sh" 'gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet'
assert_contains "$ROOT/scripts/deploy/gcp-deploy.sh" 'RELEASE_TAG="${RELEASE_TAG:-latest}"'
assert_contains "$ROOT/scripts/deploy/gcp-deploy.sh" 'BACKEND_IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/backend:${RELEASE_TAG}"'
assert_contains "$ROOT/scripts/deploy/gcp-deploy.sh" 'run-alembic-cloud.sh'
assert_contains "$ROOT/scripts/deploy/gcp-deploy.sh" 'sync-release-fixtures.sh'
assert_contains "$ROOT/scripts/deploy/gcp-deploy.sh" '--set-secrets=$backend_secret_refs'
assert_contains "$ROOT/scripts/deploy/gcp-secret-refs.py" 'versions'
assert_contains "$ROOT/scripts/deploy/render-gcp-env.py" 'Secret Manager'
assert_contains "$ROOT/scripts/deploy/build-env-file.py" 'secret overlay'
assert_contains "$ROOT/scripts/deploy/validate-versioned-config.py" 'version-controlled'
assert_contains "$ROOT/.dockerignore" '**/.env.*'
assert_contains "$ROOT/.dockerignore" '**/.git'
assert_contains "$ROOT/scripts/deploy/sync-gcp-secrets.py" '--apply'
assert_contains "$ROOT/scripts/deploy/sync-oci-secrets.py" '--apply'
assert_contains "$ROOT/scripts/deploy/rotate-encrypted-data.py" '--apply'
assert_contains "$ROOT/scripts/deploy/rotate-encrypted-data.py" 'no changes were committed'
assert_not_contains "$ROOT/scripts/deploy/gcp-deploy.sh" '--allow-unauthenticated'
assert_contains "$ROOT/scripts/deploy/oci-deploy-voice-ws.sh" 'SSH_KEY="${HOME}/${SSH_KEY#\~/}"'
assert_contains "$ROOT/scripts/deploy/oci-deploy-voice-ws.sh" 'run-alembic-cloud.sh'
assert_contains "$ROOT/scripts/deploy/oci-deploy-voice-ws.sh" 'oci-fetch-vault-env.sh'
assert_contains "$ROOT/scripts/deploy/oci-deploy-voice-ws.sh" '.dockerignore'
assert_contains "$ROOT/scripts/deploy/oci-fetch-vault-env.sh" 'instance_principal'
assert_contains "$ROOT/.github/workflows/promote-production.yml" 'deploy/config/production.env'
assert_not_contains "$ROOT/.github/workflows/promote-production.yml" 'ENV_PROD_CONFIG'
assert_contains "$ROOT/deploy/oci/docker-compose.voice-ws.yml" 'cpus: 2.0'
assert_contains "$ROOT/scripts/deploy/oci-deploy-voice-ws.sh" 'voice_nano_cpus'
assert_contains "$ROOT/scripts/deploy/run-alembic.sh" 'check_alembic_compatibility.py'
assert_contains "$ROOT/scripts/deploy/run-alembic.sh" "pg_notify('pgrst', 'reload schema')"
assert_before "$ROOT/scripts/deploy/gcp-deploy.sh" \
  '  run_deployment_migrations' \
  '  docker build --platform linux/amd64 -t "$BACKEND_IMAGE" -f backend/Dockerfile .'
assert_before "$ROOT/scripts/deploy/gcp-deploy.sh" \
  '  run_release_fixture_sync' \
  '  docker build --platform linux/amd64 -t "$BACKEND_IMAGE" -f backend/Dockerfile .'
assert_before "$ROOT/scripts/deploy/oci-deploy-voice-ws.sh" \
  'ENV_FILE="$ENV_FILE" "${ROOT}/scripts/deploy/run-alembic-cloud.sh"' \
  'rm -rf -- '\''${REMOTE_DIR}'\'''
assert_before "$ROOT/scripts/deploy/run-alembic.sh" \
  'check_alembic_compatibility.py' \
  'alembic upgrade "${REVISION}"'
assert_before "$ROOT/scripts/deploy/run-alembic.sh" \
  'alembic upgrade "${REVISION}"' \
  "pg_notify('pgrst', 'reload schema')"

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
assert_contains "$workflow" 'deploy/config/staging.env'
assert_not_contains "$workflow" 'ENV_STAGING_CONFIG: ${{ secrets.ENV_STAGING_CONFIG }}'
assert_contains "$workflow" 'render-gcp-env.py'
assert_contains "$workflow" 'check_alembic_compatibility.py --env-file .env.staging'
assert_contains "$workflow" './scripts/deploy.sh migrate --env-file .env.staging'
assert_contains "$workflow" 'GCP_PROJECT_ID: ${{ vars.STAGING_GCP_PROJECT_ID }}'
assert_not_contains "$workflow" 'migrate-production:'
assert_not_contains "$workflow" 'secrets.ENV_PROD'
assert_not_contains "$workflow" 'secrets.ENV_STAGING }}'
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
assert_contains "$production_workflow" 'deploy/config/production.env'
assert_not_contains "$production_workflow" 'ENV_PROD_CONFIG: ${{ secrets.ENV_PROD_CONFIG }}'
assert_contains "$production_workflow" 'render-gcp-env.py'
assert_contains "$production_workflow" 'deploy/config/production.env NEXT_PUBLIC_POSTHOG_KEY'
assert_contains "$production_workflow" 'LEGACY_POSTHOG_KEY: ${{ secrets.NEXT_PUBLIC_POSTHOG_KEY }}'
assert_contains "$production_workflow" 'check_alembic_compatibility.py --env-file .env.prod'
assert_contains "$production_workflow" './scripts/deploy.sh migrate --env-file .env.prod'
assert_contains "$production_workflow" 'verify_org_credential_migration.py --env-file .env.prod'
assert_contains "$production_workflow" 'name: Install GCP deployment migration dependencies'
assert_contains "$production_workflow" 'SKIP_DEPLOYMENT_MIGRATIONS: "true"'
assert_not_contains "$production_workflow" 'secrets.ENV_PROD }}'
assert_contains "$workflow" 'echo "RELEASE_TAG=$(git rev-parse HEAD)" >> "$GITHUB_ENV"'
assert_contains "$production_workflow" 'echo "RELEASE_TAG=$(git rev-parse HEAD)" >> "$GITHUB_ENV"'

# The startup guide must describe selection, never copy-to-.env switching.
assert_contains "$ROOT/README_STARTUP.md" './start.sh start dev --env staging'
assert_contains "$ROOT/README_STARTUP.md" './start.sh config --env staging'
assert_not_contains "$ROOT/README_STARTUP.md" 'cp .env.staging .env'
assert_not_contains "$ROOT/README_STARTUP.md" '| `.env` |'

echo "Environment contract tests passed."
