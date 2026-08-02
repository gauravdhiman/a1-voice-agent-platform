#!/usr/bin/env bash
# Deploy backend + frontend to Google Cloud Run using .env.cloud
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

PROJECT_ID="${GCP_PROJECT_ID:-project-bb848762-18cb-4cd6-858}"
REGION="${GCP_REGION:-us-central1}"
REPO="cognients"
ENV_FILE="${ENV_FILE:-.env.cloud}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing $ENV_FILE" >&2
  exit 1
fi

gcloud config set project "$PROJECT_ID" >/dev/null

# Read frontend build args from .env.cloud (no secrets printed)
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
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY="$(read_env NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY)"
NEXT_PUBLIC_LIVEKIT_URL="$(read_env NEXT_PUBLIC_LIVEKIT_URL)"
NEXT_PUBLIC_API_URL="$(read_env NEXT_PUBLIC_API_URL)"

BACKEND_IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/backend:latest"
FRONTEND_IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/frontend:latest"

echo "==> Ensuring Artifact Registry repository..."
if ! gcloud artifacts repositories describe "$REPO" --location="$REGION" >/dev/null 2>&1; then
  gcloud artifacts repositories create "$REPO" \
    --repository-format=docker \
    --location="$REGION" \
    --description="CogniEnts AI Platform"
fi

echo "==> Building backend image (local Docker, linux/amd64 for Cloud Run)..."
docker build --platform linux/amd64 -t "$BACKEND_IMAGE" -f backend/Dockerfile .
docker push "$BACKEND_IMAGE"

echo "==> Building frontend image (local Docker, linux/amd64 for Cloud Run)..."
docker build --platform linux/amd64 -t "$FRONTEND_IMAGE" -f frontend/Dockerfile \
  --build-arg "NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}" \
  --build-arg "NEXT_PUBLIC_SUPABASE_URL=${NEXT_PUBLIC_SUPABASE_URL}" \
  --build-arg "NEXT_PUBLIC_SUPABASE_ANON_KEY=${NEXT_PUBLIC_SUPABASE_ANON_KEY}" \
  --build-arg "NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=${NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY}" \
  --build-arg "NEXT_PUBLIC_LIVEKIT_URL=${NEXT_PUBLIC_LIVEKIT_URL}" \
  --build-arg "NEXT_PUBLIC_OTEL_ENABLED=false" \
  --build-arg "NEXT_PUBLIC_OTEL_SERVICE_NAME=cognients-frontend" \
  frontend
docker push "$FRONTEND_IMAGE"

BACKEND_ENV="$(mktemp)"
python3 scripts/deploy/gcp-env-from-cloud.py backend --env-file "$ENV_FILE" > "$BACKEND_ENV"

echo "==> Deploying backend to Cloud Run..."
gcloud run deploy cognients-backend \
  --image="$BACKEND_IMAGE" \
  --region="$REGION" \
  --platform=managed \
  --allow-unauthenticated \
  --port=8000 \
  --memory=1Gi \
  --cpu=1 \
  --min-instances=1 \
  --max-instances=10 \
  --env-vars-file="$BACKEND_ENV"

echo "==> Deploying frontend to Cloud Run..."
gcloud run deploy cognients-frontend \
  --image="$FRONTEND_IMAGE" \
  --region="$REGION" \
  --platform=managed \
  --allow-unauthenticated \
  --port=3000 \
  --memory=512Mi \
  --cpu=1 \
  --min-instances=0 \
  --max-instances=10 \
  --set-env-vars="NODE_ENV=production"

rm -f "$BACKEND_ENV"

BACKEND_URL="$(gcloud run services describe cognients-backend --region="$REGION" --format='value(status.url)')"
FRONTEND_URL="$(gcloud run services describe cognients-frontend --region="$REGION" --format='value(status.url)')"

echo ""
echo "Deploy complete."
echo "Backend:  $BACKEND_URL"
echo "Frontend: $FRONTEND_URL"
