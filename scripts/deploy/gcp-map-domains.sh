#!/usr/bin/env bash
# Map custom domains to Cloud Run services (run after gcp-deploy.sh).
# Cloud Run returns the DNS records to add in Cloudflare. Keep api/www
# DNS-only (grey cloud) for their Cloud Run managed certificates. The apex
# records are proxied so Cloudflare can apply the canonical redirect before
# the apex reaches the preview Cloud Run domain mapping.
set -euo pipefail

PROJECT_ID="${GCP_PROJECT_ID:-project-bb848762-18cb-4cd6-858}"
REGION="${GCP_REGION:-us-central1}"
API_DOMAIN="${API_DOMAIN:-api.247ai.live}"
APP_DOMAIN="${APP_DOMAIN:-www.247ai.live}"
APP_APEX_DOMAIN="${APP_APEX_DOMAIN:-247ai.live}"
BACKEND_SERVICE="${GCP_BACKEND_SERVICE:-backend-247ai}"
FRONTEND_SERVICE="${GCP_FRONTEND_SERVICE:-frontend-247ai}"

gcloud config set project "$PROJECT_ID" >/dev/null

map_domain() {
  local domain="$1"
  local service="$2"

  echo "==> Mapping $domain -> $service"
  gcloud beta run domain-mappings create \
    --service="$service" \
    --domain="$domain" \
    --region="$REGION" \
    --platform=managed 2>/dev/null || \
    gcloud beta run domain-mappings describe --domain="$domain" --region="$REGION" --platform=managed
}

map_domain "$API_DOMAIN" "$BACKEND_SERVICE"
map_domain "$APP_DOMAIN" "$FRONTEND_SERVICE"
# The apex must also be mapped to the frontend before its DNS records can
# reach the Next.js middleware and receive the permanent redirect to www.
map_domain "$APP_APEX_DOMAIN" "$FRONTEND_SERVICE"

echo ""
echo "Add the DNS records shown below in Cloudflare for 247ai.live:"
echo "  api/www: DNS only (grey cloud)"
echo "  apex: proxied (orange cloud) + Page Rule https://247ai.live/* -> https://www.247ai.live/\$1 (301)"
for domain in "$API_DOMAIN" "$APP_DOMAIN" "$APP_APEX_DOMAIN"; do
  echo "--- $domain ---"
  gcloud beta run domain-mappings describe \
    --domain="$domain" \
    --region="$REGION" \
    --platform=managed
done
