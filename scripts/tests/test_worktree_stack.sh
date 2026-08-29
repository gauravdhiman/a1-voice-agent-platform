#!/usr/bin/env bash
# Regression tests for the isolated worktree stack configuration generator.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
STACK="$ROOT/scripts/worktree-stack.sh"

assert_contains() {
  local output="$1"
  local expected="$2"
  if [[ "$output" != *"$expected"* ]]; then
    echo "Expected output to contain: $expected" >&2
    echo "$output" >&2
    exit 1
  fi
}

assert_file_contains() {
  local file="$1"
  local expected="$2"
  if ! grep -Fq -- "$expected" "$file"; then
    echo "Expected $file to contain: $expected" >&2
    exit 1
  fi
}

[[ -x "$STACK" ]] || { echo "Missing executable: $STACK" >&2; exit 1; }
bash -n "$STACK"

help_output="$($STACK help)"
assert_contains "$help_output" "up"
assert_contains "$help_output" "purge"
assert_contains "$help_output" "Supabase"

test_dir="$(mktemp -d)"
trap 'rm -rf "$test_dir"' EXIT

source_env="$test_dir/source.env"
cat > "$source_env" <<'EOF'
APP_NAME=24x7 AI
ENVIRONMENT=development
DEBUG=true
ENCRYPTION_KEY=source-key-placeholder
ENCRYPTION_KEY_FALLBACKS=invalid-fallback-placeholder
NEXT_PUBLIC_SUPABASE_URL=https://placeholder.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=source-anon-key
SUPABASE_URL=https://placeholder.supabase.co
SUPABASE_SERVICE_KEY=source-service-key
DATABASE_URL=postgresql://placeholder
JWT_SECRET_KEY=source-jwt-secret
GEMINI_API_KEY=your-gemini-api-key
EOF

state_dir="$test_dir/state"
config_output="$($STACK config \
  --name appointment-worktree \
  --port-offset 20 \
  --source-env "$source_env" \
  --state-dir "$state_dir")"

assert_contains "$config_output" "Port offset: 20"
assert_contains "$config_output" "Frontend host port: 3020"
assert_contains "$config_output" "Backend host port: 8020"
assert_contains "$config_output" "Supabase API port: 54341"
assert_contains "$config_output" "Supabase DB port: 54342"
assert_contains "$config_output" "Supabase Studio: disabled"
assert_contains "$config_output" "Frontend host port: 3020"
assert_contains "$config_output" "regular-user@247ai.local"
assert_contains "$config_output" "org-admin@247ai.local"
assert_contains "$config_output" "platform-admin@247ai.local"
assert_contains "$config_output" "Password123!"

config_file="$state_dir/supabase-project/supabase/config.toml"
app_env="$state_dir/app.env"
[[ -f "$config_file" ]] || { echo "Missing generated Supabase config" >&2; exit 1; }
[[ -f "$app_env" ]] || { echo "Missing generated app env" >&2; exit 1; }

assert_file_contains "$config_file" 'project_id = "247ai-wt-appointment-worktree-'
assert_file_contains "$config_file" 'port = 54341'
assert_file_contains "$config_file" 'port = 54342'
assert_file_contains "$config_file" 'enabled = false'
assert_file_contains "$config_file" 'site_url = "http://localhost:3020"'

python3 - "$config_file" <<'PY'
from pathlib import Path
import sys
import tomllib

config = tomllib.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
for section in ("studio", "inbucket", "edge_runtime", "analytics"):
    assert config[section]["enabled"] is False, section
for section in ("api", "auth", "realtime", "storage"):
    assert config[section]["enabled"] is True, section
PY

assert_file_contains "$app_env" 'SUPABASE_URL=http://host.docker.internal:54341'
assert_file_contains "$app_env" 'NEXT_PUBLIC_SUPABASE_URL=http://127.0.0.1:54341'
assert_file_contains "$app_env" 'DATABASE_URL=postgresql://postgres:postgres@host.docker.internal:54342/postgres'
assert_file_contains "$app_env" 'HOST_FRONTEND_PORT=3020'
assert_file_contains "$app_env" 'HOST_BACKEND_PORT=8020'
assert_file_contains "$app_env" 'VOICE_RECORDING_ENABLED=true'
assert_file_contains "$app_env" 'RECORDING_STORAGE_BACKEND=local'
assert_file_contains "$app_env" 'RECORDING_STORAGE_LOCAL_ROOT=.local-data/call-recordings'
assert_file_contains "$app_env" 'GEMINI_API_KEY=your-gemini-api-key'
assert_file_contains "$state_dir/metadata.env" 'TEST_ORGANIZATION_NAME=Pleasant Pediatric'
assert_file_contains "$state_dir/metadata.env" 'TEST_AGENT_ID=59252f36-255e-4e71-9250-c4ce3ac27eaa'

first_key="$(grep '^ENCRYPTION_KEY=' "$app_env" | cut -d= -f2-)"
[[ -n "$first_key" ]] || { echo "Missing generated encryption key" >&2; exit 1; }

valid_source_env="$test_dir/valid-source.env"
sed 's/^GEMINI_API_KEY=.*/GEMINI_API_KEY=local-test-gemini-key/' \
  "$source_env" > "$valid_source_env"

second_config_output="$($STACK config \
  --name appointment-worktree \
  --source-env "$valid_source_env" \
  --state-dir "$state_dir")"
assert_contains "$second_config_output" "Port offset: 20"
assert_file_contains "$app_env" 'GEMINI_API_KEY=local-test-gemini-key'
second_key="$(grep '^ENCRYPTION_KEY=' "$app_env" | cut -d= -f2-)"
[[ "$first_key" == "$second_key" ]] || {
  echo "Existing worktree encryption key changed on reconfiguration" >&2
  exit 1
}

if [[ "$config_output" == *"source-service-key"* ]]; then
  echo "Config output leaked a service key" >&2
  exit 1
fi
if [[ "$second_config_output" == *"local-test-gemini-key"* ]]; then
  echo "Config output leaked a Gemini key" >&2
  exit 1
fi

rotated_source_env="$test_dir/rotated-source.env"
sed 's/^GEMINI_API_KEY=.*/GEMINI_API_KEY=rotated-test-gemini-key/' \
  "$valid_source_env" > "$rotated_source_env"
$STACK config \
  --name appointment-worktree \
  --source-env "$rotated_source_env" \
  --state-dir "$state_dir" >/dev/null
assert_file_contains "$app_env" 'GEMINI_API_KEY=rotated-test-gemini-key'

python3 - "$app_env" <<'PY'
from pathlib import Path
import base64
import binascii
import sys

values = {
    line.split("=", 1)[0]: line.split("=", 1)[1]
    for line in Path(sys.argv[1]).read_text(encoding="utf-8").splitlines()
    if "=" in line
}
key = values.get("ENCRYPTION_KEY", "")
try:
    decoded = base64.urlsafe_b64decode(key.encode("ascii"))
except (ValueError, UnicodeError, binascii.Error):
    decoded = b""
assert len(key) == 44 and len(decoded) == 32
assert base64.urlsafe_b64encode(decoded).decode("ascii") == key
assert values.get("ENCRYPTION_KEY_FALLBACKS", "") == ""
PY

python3 - "$source_env" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
lines = path.read_text(encoding="utf-8").splitlines()
for index, line in enumerate(lines):
    if line.startswith("GEMINI_API_KEY="):
        lines[index] = "GEMINI_API_KEY=rotated-gemini-key"
        break
path.write_text("\n".join(lines) + "\n", encoding="utf-8")
PY

"$STACK" config \
  --name appointment-worktree \
  --port-offset 20 \
  --source-env "$source_env" \
  --state-dir "$state_dir" >/dev/null
assert_file_contains "$app_env" 'GEMINI_API_KEY=rotated-gemini-key'

if "$STACK" config --name invalid-port --port-offset 10001 --state-dir "$test_dir/invalid" >/dev/null 2>&1; then
  echo "Expected an out-of-range port offset to fail" >&2
  exit 1
fi

echo "Worktree stack configuration tests passed."
