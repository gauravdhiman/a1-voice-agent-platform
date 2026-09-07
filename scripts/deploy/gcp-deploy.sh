#!/usr/bin/env bash
# Deploy backend and/or frontend to Google Cloud Run using .env.prod.
#
# Normally invoked via ./scripts/deploy.sh; direct use is also migration-gated.
# Set GCP_DEPLOY_COMPONENT=backend|frontend|all (default: all).
# Backend deployments run the compatibility-gated database migration step
# before image build/push, including when this lower-level script is called
# directly.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

PROJECT_ID="${GCP_PROJECT_ID:-project-bb848762-18cb-4cd6-858}"
REGION="${GCP_REGION:-us-central1}"
REPO="cognients"
# Cloud Run service names must start with a letter (cannot be 247ai-...).
BACKEND_SERVICE="${GCP_BACKEND_SERVICE:-backend-247ai}"
FRONTEND_SERVICE="${GCP_FRONTEND_SERVICE:-frontend-247ai}"
ENV_FILE="${ENV_FILE:-.env.prod}"
COMPONENT="${GCP_DEPLOY_COMPONENT:-all}"
RELEASE_TAG="${RELEASE_TAG:-latest}"

if ! [[ "$RELEASE_TAG" =~ ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$ ]]; then
  echo "Invalid RELEASE_TAG: $RELEASE_TAG" >&2
  exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing $ENV_FILE" >&2
  exit 1
fi

case "$COMPONENT" in
  all|backend|frontend) ;;
  *)
    echo "Invalid GCP_DEPLOY_COMPONENT: $COMPONENT (use backend, frontend, or all)" >&2
    exit 1
    ;;
esac

run_deployment_migrations() {
  echo "==> Checking and applying database migrations before GCP deployment..."
  ENV_FILE="$ENV_FILE" "${ROOT}/scripts/deploy/run-alembic-cloud.sh"
}

run_release_fixture_sync() {
  local deployment_environment compose_project
  deployment_environment="$(
    python3 "${ROOT}/scripts/deploy/read-env-cloud.py" "$ENV_FILE" ENVIRONMENT \
      2>/dev/null || true
  )"
  deployment_environment="$(printf '%s' "$deployment_environment" | tr '[:upper:]' '[:lower:]')"
  case "$deployment_environment" in
    production) compose_project="247ai-production" ;;
    staging) compose_project="247ai-staging" ;;
    development) compose_project="247ai-development" ;;
    *)
      echo "ENVIRONMENT in $ENV_FILE must be development, staging, or production" >&2
      exit 1
      ;;
  esac

  echo "==> Synchronizing native tools and public demos before GCP deployment..."
  ENV_FILE="$ENV_FILE" COMPOSE_PROJECT_NAME="$compose_project" \
    "${ROOT}/scripts/deploy/sync-release-fixtures.sh" \
    --env-file "$ENV_FILE" \
    --project-name "$compose_project"
}

validate_backend_environment() {
  echo "==> Validating backend deployment environment..."
  python3 scripts/deploy/gcp-env-from-cloud.py backend \
    --env-file "$ENV_FILE" >/dev/null
}

# Keep the schema gate in this lower-level deployer as well as the public
# wrapper so direct component deployments cannot publish code ahead of the DB.
if [[ "$COMPONENT" == "all" || "$COMPONENT" == "backend" ]]; then
  validate_backend_environment
  run_deployment_migrations
  run_release_fixture_sync
fi

gcloud config set project "$PROJECT_ID" >/dev/null
# The GitHub Actions auth step provides gcloud credentials, but Docker does not
# use them until the Artifact Registry credential helper is configured.
gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet >/dev/null

read_env() {
  python3 - "$1" "$ENV_FILE" <<'PY'
import sys
from pathlib import Path
key, path = sys.argv[1], Path(sys.argv[2])
for line in path.read_text().splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, _, v = line.partition("=")
    if k.strip() == key:
        print(v.strip())
        break
PY
}

NEXT_PUBLIC_SUPABASE_URL="$(read_env NEXT_PUBLIC_SUPABASE_URL)"
NEXT_PUBLIC_SUPABASE_ANON_KEY="$(read_env NEXT_PUBLIC_SUPABASE_ANON_KEY)"
NEXT_PUBLIC_GOOGLE_CLIENT_ID="$(read_env NEXT_PUBLIC_GOOGLE_CLIENT_ID)"
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY="$(read_env NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY)"
NEXT_PUBLIC_API_URL="$(read_env NEXT_PUBLIC_API_URL)"
NEXT_PUBLIC_APP_NAME="$(read_env NEXT_PUBLIC_APP_NAME)"
NEXT_PUBLIC_APP_DESCRIPTION="$(read_env NEXT_PUBLIC_APP_DESCRIPTION)"

BACKEND_IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/backend:${RELEASE_TAG}"
FRONTEND_IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/frontend:${RELEASE_TAG}"

echo "==> Ensuring Artifact Registry repository..."
if ! gcloud artifacts repositories describe "$REPO" --location="$REGION" >/dev/null 2>&1; then
  gcloud artifacts repositories create "$REPO" \
    --repository-format=docker \
    --location="$REGION" \
    --description="247ai.live platform images"
fi

deploy_backend() {
  echo "==> Building backend image (local Docker, linux/amd64 for Cloud Run)..."
  docker build --platform linux/amd64 -t "$BACKEND_IMAGE" -f backend/Dockerfile .
  docker push "$BACKEND_IMAGE"

  local backend_env
  backend_env="$(mktemp)"
  python3 scripts/deploy/gcp-env-from-cloud.py backend --env-file "$ENV_FILE" > "$backend_env"

  echo "==> Deploying backend to Cloud Run ($BACKEND_SERVICE, tag ${RELEASE_TAG})..."
  gcloud run deploy "$BACKEND_SERVICE" \
    --image="$BACKEND_IMAGE" \
    --region="$REGION" \
    --platform=managed \
    --port=8000 \
    --memory=1Gi \
    --cpu=1 \
    --min-instances=1 \
    --max-instances=10 \
    --env-vars-file="$backend_env"

  rm -f "$backend_env"
}

deploy_frontend() {
  echo "==> Building frontend image (local Docker, linux/amd64 for Cloud Run)..."
  docker build --platform linux/amd64 -t "$FRONTEND_IMAGE" -f frontend/Dockerfile \
    --build-arg "NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}" \
    --build-arg "NEXT_PUBLIC_SUPABASE_URL=${NEXT_PUBLIC_SUPABASE_URL}" \
    --build-arg "NEXT_PUBLIC_SUPABASE_ANON_KEY=${NEXT_PUBLIC_SUPABASE_ANON_KEY}" \
    --build-arg "NEXT_PUBLIC_GOOGLE_CLIENT_ID=${NEXT_PUBLIC_GOOGLE_CLIENT_ID}" \
    --build-arg "NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=${NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY}" \
    --build-arg "NEXT_PUBLIC_APP_NAME=${NEXT_PUBLIC_APP_NAME}" \
    --build-arg "NEXT_PUBLIC_APP_DESCRIPTION=${NEXT_PUBLIC_APP_DESCRIPTION}" \
    --build-arg "NEXT_PUBLIC_OTEL_ENABLED=false" \
    --build-arg "NEXT_PUBLIC_OTEL_SERVICE_NAME=frontend-247ai" \
    frontend
  docker push "$FRONTEND_IMAGE"

  echo "==> Deploying frontend to Cloud Run ($FRONTEND_SERVICE, tag ${RELEASE_TAG})..."
  gcloud run deploy "$FRONTEND_SERVICE" \
    --image="$FRONTEND_IMAGE" \
    --region="$REGION" \
    --platform=managed \
    --port=3000 \
    --memory=512Mi \
    --cpu=1 \
    --min-instances=0 \
    --max-instances=10 \
    --set-env-vars="NODE_ENV=production,NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}"
}

if [[ "$COMPONENT" == "all" || "$COMPONENT" == "backend" ]]; then
  deploy_backend
fi

if [[ "$COMPONENT" == "all" || "$COMPONENT" == "frontend" ]]; then
  deploy_frontend
fi

if [[ "$COMPONENT" == "backend" ]]; then
  BACKEND_URL="$(gcloud run services describe "$BACKEND_SERVICE" --region="$REGION" --format='value(status.url)')"
  echo ""
  echo "Backend deploy complete: $BACKEND_URL"
elif [[ "$COMPONENT" == "frontend" ]]; then
  FRONTEND_URL="$(gcloud run services describe "$FRONTEND_SERVICE" --region="$REGION" --format='value(status.url)')"
  echo ""
  echo "Frontend deploy complete: $FRONTEND_URL"
else
  BACKEND_URL="$(gcloud run services describe "$BACKEND_SERVICE" --region="$REGION" --format='value(status.url)')"
  FRONTEND_URL="$(gcloud run services describe "$FRONTEND_SERVICE" --region="$REGION" --format='value(status.url)')"
  echo ""
  echo "Deploy complete."
  echo "Backend:  $BACKEND_URL"
  echo "Frontend: $FRONTEND_URL"
  echo "Custom domains: https://api.247ai.live  /  https://www.247ai.live"
  echo "Canonical redirect: https://247ai.live -> https://www.247ai.live"
  echo "(Direct *.run.app Host is blocked in production — use the custom domains.)"
fi
