#!/usr/bin/env bash
# Deploy the private maintenance worker after reviewed migration and provisioning.
# This is a separate, explicit release step; it does not switch the API mode.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
: "${GCP_PROJECT_ID:?Set GCP_PROJECT_ID explicitly}"
: "${GCP_BACKEND_RUNTIME_SERVICE_ACCOUNT:?Set the worker runtime service account}"
: "${GCP_SECRET_NAME_PREFIX:?Set the backend secret prefix}"
: "${MAINTENANCE_AUTH_SECRET_REF:?Set SECRET_NAME:NUMERIC_VERSION}"
: "${MAINTENANCE_HEARTBEAT_SECRET_REF:?Set SECRET_NAME:NUMERIC_VERSION}"
: "${RELEASE_TAG:?Set the reviewed immutable release tag}"
ENV_FILE="${ENV_FILE:-.env.prod}"
REGION="${GCP_REGION:-us-central1}"
SERVICE="${GCP_MAINTENANCE_SERVICE:-maintenance-247ai}"
REPO="${GCP_ARTIFACT_REPOSITORY:-cognients}"

for ref in "$MAINTENANCE_AUTH_SECRET_REF" "$MAINTENANCE_HEARTBEAT_SECRET_REF"; do
  if [[ ! "$ref" =~ ^[A-Za-z0-9_-]+:[0-9]+$ ]]; then
    echo "Maintenance secret references must be local secret IDs with numeric versions" >&2
    exit 1
  fi
done
if [[ ! "$RELEASE_TAG" =~ ^[a-f0-9]{40}$ ]]; then
  echo "RELEASE_TAG must be a reviewed full commit SHA" >&2
  exit 1
fi
if [[ "$(git rev-parse HEAD)" != "$RELEASE_TAG" ]] || [[ -n "$(git status --porcelain)" ]]; then
  echo "Deploy only a clean checkout at the reviewed release SHA" >&2
  exit 1
fi
[[ -f "$ENV_FILE" ]] || { echo "Missing deployment environment file" >&2; exit 1; }
env_file="$(mktemp)"
trap 'rm -f "$env_file"' EXIT
python3 scripts/deploy/gcp-env-from-cloud.py backend --env-file "$ENV_FILE" \
  --secret-mode gcp > "$env_file"
secret_refs="$(python3 scripts/deploy/gcp-secret-refs.py \
  --env-file "$ENV_FILE" --project "$GCP_PROJECT_ID" --service backend \
  --secret-prefix "$GCP_SECRET_NAME_PREFIX")"
secret_refs+=",MAINTENANCE_AUTH_TOKEN=$MAINTENANCE_AUTH_SECRET_REF"
secret_refs+=",MAINTENANCE_HEARTBEAT_URL=$MAINTENANCE_HEARTBEAT_SECRET_REF"
image="${REGION}-docker.pkg.dev/${GCP_PROJECT_ID}/${REPO}/maintenance:${RELEASE_TAG}"
docker build --platform linux/amd64 --target maintenance -t "$image" -f backend/Dockerfile .
docker push "$image"
gcloud run deploy "$SERVICE" --project="$GCP_PROJECT_ID" --region="$REGION" \
  --image="$image" --platform=managed --port=8000 --memory=1Gi --cpu=1 \
  --min-instances=0 --max-instances=2 --concurrency=1 --timeout=900 \
  --cpu-throttling --no-allow-unauthenticated \
  --service-account="$GCP_BACKEND_RUNTIME_SERVICE_ACCOUNT" \
  --env-vars-file="$env_file" --set-secrets="$secret_refs"
