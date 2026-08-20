#!/usr/bin/env bash
# Single entry point for production deployment (247ai.live).
#
# Credentials live only in .env.prod (gitignored). This script never prints secrets.
#
# Usage:
#   ./scripts/deploy.sh [component] [options]
#
# Components:
#   all         Deploy backend + frontend (GCP) and voice-ws worker (OCI). Default.
#   gcp         Deploy backend + frontend on GCP only (no OCI voice-ws)
#   backend     GCP Cloud Run backend only
#   frontend    GCP Cloud Run frontend only
#   voice-ws    OCI voice-ws WebSocket worker (Pipecat). Alias: voice, worker
#   migrate     Run Alembic migrations against production Supabase
#   verify-data Verify production phone-number data migration postconditions
#   domains     Map api/www custom domains to Cloud Run services
#
# Options:
#   --env-file PATH   Env file (default: .env.prod at repo root)
#   -h, --help        Show this help
#
# voice-ws requires OCI SSH env vars (not stored in .env.prod):
#   OCI_SSH_HOST      VM public IP
#   OCI_SSH_USER      SSH user (default: ubuntu)
#   OCI_SSH_KEY       Path to private key (default: ~/.ssh/oci_voice_ws)
#
# Examples:
#   ./scripts/deploy.sh
#   ./scripts/deploy.sh backend
#   ./scripts/deploy.sh frontend
#   ./scripts/deploy.sh voice-ws
#   OCI_SSH_HOST=203.0.113.10 ./scripts/deploy.sh worker
#   ./scripts/deploy.sh migrate
#   ./scripts/deploy.sh verify-data
#
# Cloud Run image tags default to ``latest`` for local/manual use. CI sets
# RELEASE_TAG to the checked-out commit SHA so staging and production can use
# an immutable release tag.
#
# Full runbook: docs/05_operations/deployment/runbook.md
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEPLOY_DIR="${ROOT}/scripts/deploy"

COMPONENT="all"
ENV_FILE="${ENV_FILE:-${ROOT}/.env.prod}"

usage() {
  sed -n '3,33p' "$0" | sed 's/^# \{0,1\}//'
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --env-file)
      [[ $# -ge 2 ]] || { echo "Missing value for --env-file" >&2; exit 1; }
      ENV_FILE="$2"
      shift 2
      ;;
    -h|--help|help)
      usage
      exit 0
      ;;
    all|gcp|backend|frontend|voice-ws|voice|worker|migrate|migrations|db|verify-data|verify-phone-numbers|domains|dns)
      COMPONENT="$1"
      shift
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

export ENV_FILE

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing env file: $ENV_FILE" >&2
  echo "Copy .env.prod.example to .env.prod and fill in your production values." >&2
  exit 1
fi

run_gcp() {
  local target="${1:-all}"
  GCP_DEPLOY_COMPONENT="$target" "${DEPLOY_DIR}/gcp-deploy.sh"
}

run_voice_ws() {
  "${DEPLOY_DIR}/oci-deploy-voice-ws.sh"
}

case "$COMPONENT" in
  all)
    run_gcp all
    if [[ -z "${OCI_SSH_HOST:-}" ]]; then
      echo ""
      echo "Skipping voice-ws: OCI_SSH_HOST is not set."
      echo "Deploy voice-ws later: OCI_SSH_HOST=<ip> ./scripts/deploy.sh voice-ws"
    else
      run_voice_ws
    fi
    ;;
  gcp)
    run_gcp all
    ;;
  backend|frontend)
    run_gcp "$COMPONENT"
    ;;
  voice-ws|voice|worker)
    run_voice_ws
    ;;
  migrate|migrations|db)
    "${DEPLOY_DIR}/run-alembic-cloud.sh"
    ;;
  verify-data|verify-phone-numbers)
    python3 "${DEPLOY_DIR}/verify_phone_number_backfill.py" --env-file "$ENV_FILE"
    ;;
  domains|dns)
    "${DEPLOY_DIR}/gcp-map-domains.sh"
    ;;
  *)
    echo "Unknown component: $COMPONENT" >&2
    usage >&2
    exit 1
    ;;
esac
