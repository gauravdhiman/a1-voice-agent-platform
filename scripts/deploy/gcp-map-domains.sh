#!/usr/bin/env bash
# Map custom domains to Cloud Run services (run after gcp-deploy.sh).
set -euo pipefail

PROJECT_ID="${GCP_PROJECT_ID:-project-bb848762-18cb-4cd6-858}"
REGION="${GCP_REGION:-us-central1}"
API_DOMAIN="${API_DOMAIN:-ai-studio-api.cognients.com}"
APP_DOMAIN="${APP_DOMAIN:-ai-studio.cognients.com}"

gcloud config set project "$PROJECT_ID" >/dev/null

echo "==> Mapping $API_DOMAIN -> cognients-backend"
gcloud beta run domain-mappings create \
  --service=cognients-backend \
  --domain="$API_DOMAIN" \
  --region="$REGION" \
  --platform=managed 2>/dev/null || \
  gcloud beta run domain-mappings describe --domain="$API_DOMAIN" --region="$REGION" --platform=managed

echo "==> Mapping $APP_DOMAIN -> cognients-frontend"
gcloud beta run domain-mappings create \
  --service=cognients-frontend \
  --domain="$APP_DOMAIN" \
  --region="$REGION" \
  --platform=managed 2>/dev/null || \
  gcloud beta run domain-mappings describe --domain="$APP_DOMAIN" --region="$REGION" --platform=managed

echo ""
echo "Add these DNS records in Cloudflare for cognients.com:"
gcloud beta run domain-mappings describe --domain="$API_DOMAIN" --region="$REGION" --platform=managed
echo "---"
gcloud beta run domain-mappings describe --domain="$APP_DOMAIN" --region="$REGION" --platform=managed
