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
assert_contains "$ROOT/docker-compose.dev.yml" '${ENV_FILE:-.env.local}'
assert_contains "$ROOT/docker-compose.yml" '${ENV_FILE:-.env.prod}'
assert_contains "$ROOT/scripts/deploy.sh" '${ROOT}/.env.prod'
assert_contains "$ROOT/scripts/deploy/gcp-deploy.sh" 'gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet'
assert_not_contains "$ROOT/scripts/deploy/gcp-deploy.sh" '--allow-unauthenticated'

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

workflow="$ROOT/.github/workflows/deploy-cloud.yml"
assert_not_contains "$workflow" 'if: ${{ secrets.OCI_SSH_KEY != '\'''\'' }}'
assert_contains "$workflow" 'id: check-oci-ssh-key'
assert_contains "$workflow" 'OCI_SSH_KEY: ${{ secrets.OCI_SSH_KEY }}'
assert_contains "$workflow" 'if: steps.check-oci-ssh-key.outputs.configured == '\''true'\'''

# The startup guide must describe selection, never copy-to-.env switching.
assert_contains "$ROOT/README_STARTUP.md" './start.sh start dev --env staging'
assert_contains "$ROOT/README_STARTUP.md" './start.sh config --env staging'
assert_not_contains "$ROOT/README_STARTUP.md" 'cp .env.staging .env'
assert_not_contains "$ROOT/README_STARTUP.md" '| `.env` |'

echo "Environment contract tests passed."
