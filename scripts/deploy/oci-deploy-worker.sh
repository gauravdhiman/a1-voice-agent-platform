#!/usr/bin/env bash
# Deploy LiveKit worker to an OCI VM (Docker + compose).
# Prerequisites on VM: Docker, docker compose, outbound internet.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

ENV_FILE="${ENV_FILE:-.env.cloud}"
WORKER_IMAGE="${WORKER_IMAGE:-us-central1-docker.pkg.dev/project-bb848762-18cb-4cd6-858/cognients/worker:latest}"
OCI_HOST="${OCI_SSH_HOST:?Set OCI_SSH_HOST}"
OCI_USER="${OCI_SSH_USER:-ubuntu}"
SSH_KEY="${OCI_SSH_KEY:-${HOME}/.ssh/id_rsa}"

python3 scripts/deploy/gcp-env-from-cloud.py worker --env-file "$ENV_FILE" > /tmp/cognients-worker.env

echo "==> Syncing worker files to ${OCI_USER}@${OCI_HOST}..."
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=accept-new "${OCI_USER}@${OCI_HOST}" "mkdir -p ~/cognients-worker"
scp -i "$SSH_KEY" /tmp/cognients-worker.env "${OCI_USER}@${OCI_HOST}:~/cognients-worker/.env.worker"
scp -i "$SSH_KEY" deploy/oci/docker-compose.worker.yml "${OCI_USER}@${OCI_HOST}:~/cognients-worker/docker-compose.worker.yml"

echo "==> Pulling and starting worker..."
ssh -i "$SSH_KEY" "${OCI_USER}@${OCI_HOST}" bash -s <<EOF
set -euo pipefail
cd ~/cognients-worker
export WORKER_IMAGE=${WORKER_IMAGE}
docker pull "\$WORKER_IMAGE"
docker compose -f docker-compose.worker.yml up -d --remove-orphans
docker compose -f docker-compose.worker.yml ps
EOF

rm -f /tmp/cognients-worker.env
echo "Worker deploy complete."
