#!/usr/bin/env bash
# Deploy the voice-ws (Pipecat WebSocket) worker to an OCI VM.
#
# Builds the voice-ws image *on the VM* from synced repo source (no GCP Artifact
# Registry, no cross-cloud auth, works on ARM A1 Flex). Caddy fronts voice-ws on
# 80/443 with automatic Let's Encrypt TLS for voice.<domain>.
#
# Prerequisites on the VM: Docker, docker compose plugin, OCI CLI configured for
# instance principals, ports 80/443 open (OCI security list + iptables), and a
# DNS A record voice.247ai.live -> VM IP. The cloud database migration gate
# runs before any remote files are replaced unless the caller has already run
# the shared release migration gate.
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
if [[ "$REMOTE_DIR" == /* || "$REMOTE_DIR" == "." || "$REMOTE_DIR" == ".." || \
      "$REMOTE_DIR" == *".."* || ! "$REMOTE_DIR" =~ ^[A-Za-z0-9][A-Za-z0-9._/-]*$ ]]; then
  echo "OCI_REMOTE_DIR must be a safe relative path below the SSH user's home" >&2
  exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing $ENV_FILE" >&2
  exit 1
fi

read_env() {
  python3 - "$1" "$ENV_FILE" <<'PY'
import sys
from pathlib import Path
key, path = sys.argv[1], Path(sys.argv[2])
for line in path.read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    candidate, _, value = line.partition("=")
    if candidate.strip() == key:
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
            value = value[1:-1]
        print(value)
        break
PY
}

SECRET_MANAGER_MODE="$(read_env SECRET_MANAGER_MODE || true)"
SECRET_MANAGER_MODE="${SECRET_MANAGER_MODE:-env}"
case "$SECRET_MANAGER_MODE" in
  env|gcp) ;;
  *)
    echo "SECRET_MANAGER_MODE must be env or gcp" >&2
    exit 1
    ;;
esac
OCI_VAULT_ID="$(read_env OCI_VAULT_ID || true)"
OCI_SECRET_NAME_PREFIX="$(read_env OCI_SECRET_NAME_PREFIX || true)"
SKIP_DEPLOYMENT_MIGRATIONS="${SKIP_DEPLOYMENT_MIGRATIONS:-false}"

use_oci_vault=false
if [[ -n "$OCI_VAULT_ID" && -n "$OCI_SECRET_NAME_PREFIX" ]]; then
  use_oci_vault=true
fi
if [[ "$SECRET_MANAGER_MODE" == "gcp" && "$use_oci_vault" != true ]]; then
  echo "OCI_VAULT_ID and OCI_SECRET_NAME_PREFIX are required for managed voice-ws secrets" >&2
  exit 1
fi
if [[ "$SKIP_DEPLOYMENT_MIGRATIONS" == "true" && "$use_oci_vault" != true ]]; then
  echo "SKIP_DEPLOYMENT_MIGRATIONS=true requires OCI Vault secret bootstrap" >&2
  exit 1
fi

echo "==> Validating voice-ws deployment environment..."
if [[ "$use_oci_vault" == true ]]; then
  python3 scripts/deploy/gcp-env-from-cloud.py voice-ws \
    --env-file "$ENV_FILE" \
    --public-only \
    --format dotenv >/dev/null
else
  python3 scripts/deploy/gcp-env-from-cloud.py voice-ws \
    --env-file "$ENV_FILE" \
    --secret-mode "$SECRET_MANAGER_MODE" \
    --format dotenv >/dev/null
fi

if [[ "$SKIP_DEPLOYMENT_MIGRATIONS" == "true" ]]; then
  echo "==> Skipping voice-ws migration gate; caller already completed it."
else
  echo "==> Checking and applying database migrations before voice-ws deployment..."
  ENV_FILE="$ENV_FILE" "${ROOT}/scripts/deploy/run-alembic-cloud.sh"
  python3 "${ROOT}/scripts/deploy/verify_org_credential_migration.py" \
    --env-file "$ENV_FILE"
fi

echo "==> Preparing voice-ws environment files..."
voice_env_file="$(mktemp /tmp/247ai-voice-ws-env.XXXXXX)"
voice_public_env_file="$(mktemp /tmp/247ai-voice-ws-public.XXXXXX)"
voice_secret_manifest_file="$(mktemp /tmp/247ai-voice-ws-manifest.XXXXXX)"
trap 'rm -f "$voice_env_file" "$voice_public_env_file" "$voice_secret_manifest_file"' EXIT
if [[ "$use_oci_vault" == true ]]; then
  python3 scripts/deploy/gcp-env-from-cloud.py voice-ws \
    --env-file "$ENV_FILE" \
    --public-only \
    --format dotenv > "$voice_public_env_file"
  python3 scripts/deploy/gcp-env-from-cloud.py voice-ws \
    --env-file "$ENV_FILE" \
    --secret-manifest \
    --secret-prefix "$OCI_SECRET_NAME_PREFIX" > "$voice_secret_manifest_file"
else
  python3 scripts/deploy/gcp-env-from-cloud.py voice-ws \
    --env-file "$ENV_FILE" \
    --secret-mode "$SECRET_MANAGER_MODE" \
    --format dotenv > "$voice_env_file"
fi

echo "==> Syncing source + compose + Caddyfile to ${OCI_USER}@${OCI_HOST}:${REMOTE_DIR}..."
ssh "${SSH_OPTS[@]}" "${OCI_USER}@${OCI_HOST}" \
  "rm -rf -- '${REMOTE_DIR}' && mkdir -p -- '${REMOTE_DIR}'"
# Sync the repo-root layout the voice-ws Dockerfile build context expects:
# REMOTE_DIR/shared/ + REMOTE_DIR/voice-ws/ as siblings (no trailing slashes,
# so the source dirs are preserved rather than flattened into the remote root).
rsync -az \
  -e "ssh ${SSH_OPTS[*]}" \
  --exclude='__pycache__' --exclude='.pytest_cache' --exclude='tests' \
  shared voice-ws \
  "${OCI_USER}@${OCI_HOST}:${REMOTE_DIR}/"
scp "${SSH_OPTS[@]}" \
  .dockerignore \
  "${OCI_USER}@${OCI_HOST}:${REMOTE_DIR}/.dockerignore"
scp "${SSH_OPTS[@]}" \
  deploy/oci/docker-compose.voice-ws.yml \
  deploy/oci/Caddyfile \
  "${OCI_USER}@${OCI_HOST}:${REMOTE_DIR}/"
if [[ "$use_oci_vault" == true ]]; then
  scp "${SSH_OPTS[@]}" \
    "$voice_public_env_file" \
    scripts/deploy/oci-fetch-vault-env.sh \
    "${OCI_USER}@${OCI_HOST}:${REMOTE_DIR}/"
  scp "${SSH_OPTS[@]}" \
    "$voice_secret_manifest_file" \
    "${OCI_USER}@${OCI_HOST}:${REMOTE_DIR}/.voice-ws.secret-manifest"
  ssh "${SSH_OPTS[@]}" "${OCI_USER}@${OCI_HOST}" \
    "mv -- '${REMOTE_DIR}/$(basename "$voice_public_env_file")' '${REMOTE_DIR}/.env.voice-ws-public'"
else
  scp "${SSH_OPTS[@]}" \
    "$voice_env_file" \
    "${OCI_USER}@${OCI_HOST}:${REMOTE_DIR}/.env.voice-ws"
fi

echo "==> Building and starting voice-ws + Caddy on the VM..."
ssh "${SSH_OPTS[@]}" "${OCI_USER}@${OCI_HOST}" bash -s -- \
  "$REMOTE_DIR" "$use_oci_vault" <<'EOF'
set -euo pipefail
REMOTE_DIR="$1"
USE_OCI_VAULT="$2"
cd -- "$REMOTE_DIR"
if [[ "$USE_OCI_VAULT" == "true" ]]; then
  chmod 700 oci-fetch-vault-env.sh
  ./oci-fetch-vault-env.sh .env.voice-ws-public .voice-ws.secret-manifest .env.voice-ws
  rm -f .env.voice-ws-public .voice-ws.secret-manifest oci-fetch-vault-env.sh
  chmod 600 .env.voice-ws
fi
docker compose -f docker-compose.voice-ws.yml up -d --build --remove-orphans
voice_container_id="$(docker compose -f docker-compose.voice-ws.yml ps -q voice-ws)"
if [[ -z "${voice_container_id}" ]]; then
  echo "voice-ws container was not created" >&2
  exit 1
fi
voice_nano_cpus="$(docker inspect --format='{{.HostConfig.NanoCpus}}' "${voice_container_id}")"
if [[ "${voice_nano_cpus}" != "2000000000" ]]; then
  echo "voice-ws CPU limit is ${voice_nano_cpus} nano CPUs; expected 2000000000" >&2
  exit 1
fi
echo "voice-ws CPU limit: ${voice_nano_cpus} nano CPUs (2 OCPU ceiling)"
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
