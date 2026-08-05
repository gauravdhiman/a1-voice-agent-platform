#!/usr/bin/env bash
# Map custom domains to Cloud Run services (run after gcp-deploy.sh).
# Both domains are subdomains of 247ai.live — Cloud Run returns CNAME targets to
# add in Cloudflare (grey cloud / DNS-only so Cloud Run serves the managed cert).
set -euo pipefail

PROJECT_ID="${GCP_PROJECT_ID:-project-bb848762-18cb-4cd6-858}"
REGION="${GCP_REGION:-us-central1}"
API_DOMAIN="${API_DOMAIN:-api.247ai.live}"
APP_DOMAIN="${APP_DOMAIN:-www.247ai.live}"
BACKEND_SERVICE="${GCP_BACKEND_SERVICE:-backend-247ai}"
FRONTEND_SERVICE="${GCP_FRONTEND_SERVICE:-frontend-247ai}"

gcloud config set project "$PROJECT_ID" >/dev/null

echo "==> Mapping $API_DOMAIN -> $BACKEND_SERVICE"
gcloud beta run domain-mappings create \
  --service="$BACKEND_SERVICE" \
  --domain="$API_DOMAIN" \
  --region="$REGION" \
  --platform=managed 2>/dev/null || \
  gcloud beta run domain-mappings describe --domain="$API_DOMAIN" --region="$REGION" --platform=managed

echo "==> Mapping $APP_DOMAIN -> $FRONTEND_SERVICE"
gcloud beta run domain-mappings create \
  --service="$FRONTEND_SERVICE" \
  --domain="$APP_DOMAIN" \
  --region="$REGION" \
  --platform=managed 2>/dev/null || \
  gcloud beta run domain-mappings describe --domain="$APP_DOMAIN" --region="$REGION" --platform=managed

echo ""
echo "Add these CNAME records in Cloudflare for 247ai.live (grey cloud / DNS only):"
gcloud beta run domain-mappings describe --domain="$API_DOMAIN" --region="$REGION" --platform=managed
echo "---"
gcloud beta run domain-mappings describe --domain="$APP_DOMAIN" --region="$REGION" --platform=managed
