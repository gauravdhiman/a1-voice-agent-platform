#!/usr/bin/env bash
# Deploy the voice-ws (Pipecat WebSocket) worker to an OCI VM.
#
# Builds the voice-ws image *on the VM* from synced repo source (no GCP Artifact
# Registry, no cross-cloud auth, works on ARM A1 Flex). Caddy fronts voice-ws on
# 80/443 with automatic Let's Encrypt TLS for voice.<domain>.
#
# Prerequisites on the VM: Docker, docker compose plugin, ports 80/443 open
# (OCI security list + iptables), and a DNS A record voice.247ai.live -> VM IP.
# The cloud database migration gate runs before any remote files are replaced.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

ENV_FILE="${ENV_FILE:-.env.prod}"
OCI_HOST="${OCI_SSH_HOST:?Set OCI_SSH_HOST (VM public IP)}"
OCI_USER="${OCI_SSH_USER:-ubuntu}"
SSH_KEY="${OCI_SSH_KEY:-${HOME}/.ssh/oci_voice_ws}"
# Expand leading ~ (env vars from .bashrc often keep a literal tilde).
if [[ "$SSH_KEY" == "~/"* ]]; then
  SSH_KEY="${HOME}/${SSH_KEY#\~/}"
elif [[ "$SSH_KEY" == "~" ]]; then
  SSH_KEY="$HOME"
fi
# Relative paths are resolved from the repo root.
if [[ "$SSH_KEY" != /* ]]; then
  SSH_KEY="${ROOT}/${SSH_KEY}"
fi
if [[ ! -f "$SSH_KEY" ]]; then
  echo "SSH private key not found: $SSH_KEY" >&2
  echo "Set OCI_SSH_KEY to your OCI VM private key, e.g.:" >&2
  echo "  export OCI_SSH_KEY=~/.ssh/oci_voice_ws" >&2
  echo "  OCI_SSH_HOST=<vm-ip> ./scripts/deploy.sh voice-ws" >&2
  exit 1
fi

# SSH refuses private keys that are readable by group/others.
key_mode="$(stat -f '%OLp' "$SSH_KEY" 2>/dev/null || stat -c '%a' "$SSH_KEY" 2>/dev/null || echo "")"
if [[ "$key_mode" == "644" || "$key_mode" == "664" || "$key_mode" == "666" || "$key_mode" == "755" ]]; then
  echo "==> Fixing SSH key permissions (was ${key_mode}, need 600): $SSH_KEY"
  chmod 600 "$SSH_KEY"
fi

SSH_OPTS=(-i "$SSH_KEY" -o StrictHostKeyChecking=accept-new)

echo "==> Testing SSH to ${OCI_USER}@${OCI_HOST}..."
if ! ssh "${SSH_OPTS[@]}" -o BatchMode=yes -o ConnectTimeout=15 "${OCI_USER}@${OCI_HOST}" "echo ok" >/dev/null 2>&1; then
  pub_key="${SSH_KEY%.key}.key.pub"
  [[ -f "$pub_key" ]] || pub_key="${SSH_KEY}.pub"
  cat >&2 <<EOF

SSH authentication failed for ${OCI_USER}@${OCI_HOST}.

The private key is readable, but the VM does not accept it. Common causes:
  1. This public key was not added when the OCI instance was created.
  2. A different SSH key was pasted into the OCI "SSH keys" field at launch.

Fix (pick one):
  A) OCI Console → Compute → Instances → your VM → More actions →
     "Reset instance SSH keys" (or recreate with the correct public key).
  B) OCI Console → Instance → Create console connection → connect and append
     your public key to ~/.ssh/authorized_keys for user ${OCI_USER}.

Your public key file (paste into OCI or authorized_keys):
  ${pub_key:-<not found — run: ssh-keygen -y -f "$SSH_KEY" > my-key.pub>}

Test manually:
  ssh -i "$SSH_KEY" ${OCI_USER}@${OCI_HOST} "echo ok"

EOF
  exit 1
fi

# Relative to the VM user's home (SSH/scp/rsync resolve it against the remote home).
REMOTE_DIR="${OCI_REMOTE_DIR:-voice-ws}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing $ENV_FILE" >&2
  exit 1
fi

echo "==> Validating voice-ws deployment environment..."
python3 scripts/deploy/gcp-env-from-cloud.py voice-ws \
  --env-file "$ENV_FILE" >/dev/null

echo "==> Checking and applying database migrations before voice-ws deployment..."
ENV_FILE="$ENV_FILE" "${ROOT}/scripts/deploy/run-alembic-cloud.sh"

echo "==> Generating .env.voice-ws from $ENV_FILE..."
voice_env_file="$(mktemp /tmp/247ai-voice-ws-env.XXXXXX)"
trap 'rm -f "$voice_env_file"' EXIT
python3 scripts/deploy/gcp-env-from-cloud.py voice-ws --env-file "$ENV_FILE" > "$voice_env_file"

echo "==> Syncing source + compose + Caddyfile to ${OCI_USER}@${OCI_HOST}:${REMOTE_DIR}..."
ssh "${SSH_OPTS[@]}" "${OCI_USER}@${OCI_HOST}" "rm -rf ${REMOTE_DIR} && mkdir -p ${REMOTE_DIR}"
# Sync the repo-root layout the voice-ws Dockerfile build context expects:
# REMOTE_DIR/shared/ + REMOTE_DIR/voice-ws/ as siblings (no trailing slashes,
# so the source dirs are preserved rather than flattened into the remote root).
rsync -az \
  -e "ssh ${SSH_OPTS[*]}" \
  --exclude='__pycache__' --exclude='.pytest_cache' --exclude='tests' \
  shared voice-ws \
  "${OCI_USER}@${OCI_HOST}:${REMOTE_DIR}/"
scp "${SSH_OPTS[@]}" \
  deploy/oci/docker-compose.voice-ws.yml \
  deploy/oci/Caddyfile \
  "${OCI_USER}@${OCI_HOST}:${REMOTE_DIR}/"
scp "${SSH_OPTS[@]}" \
  "$voice_env_file" \
  "${OCI_USER}@${OCI_HOST}:${REMOTE_DIR}/.env.voice-ws"

echo "==> Building and starting voice-ws + Caddy on the VM..."
ssh "${SSH_OPTS[@]}" "${OCI_USER}@${OCI_HOST}" bash -s <<EOF
set -euo pipefail
cd ${REMOTE_DIR}
docker compose -f docker-compose.voice-ws.yml up -d --build --remove-orphans
voice_container_id="\$(docker compose -f docker-compose.voice-ws.yml ps -q voice-ws)"
if [[ -z "\${voice_container_id}" ]]; then
  echo "voice-ws container was not created" >&2
  exit 1
fi
voice_nano_cpus="\$(docker inspect --format='{{.HostConfig.NanoCpus}}' "\${voice_container_id}")"
if [[ "\${voice_nano_cpus}" != "2000000000" ]]; then
  echo "voice-ws CPU limit is \${voice_nano_cpus} nano CPUs; expected 2000000000" >&2
  exit 1
fi
echo "voice-ws CPU limit: \${voice_nano_cpus} nano CPUs (2 OCPU ceiling)"
docker compose -f docker-compose.voice-ws.yml ps
echo "--- voice-ws logs (last 20) ---"
docker compose -f docker-compose.voice-ws.yml logs --tail=20 voice-ws
echo "--- caddy logs (last 20) ---"
docker compose -f docker-compose.voice-ws.yml logs --tail=20 caddy
EOF

cat <<EOF

voice-ws deploy complete.

Next steps:
  1. Ensure an A record  voice.247ai.live  ->  ${OCI_HOST}  exists (grey-cloud DNS).
  2. Ensure OCI ingress 80/443 is open (security list + iptables).
  3. Caddy will auto-issue a Let's Encrypt cert on first request. Verify:
       curl https://voice.247ai.live/health
EOF
