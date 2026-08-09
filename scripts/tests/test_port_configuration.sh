#!/usr/bin/env bash
# Regression tests for the shared Docker host-port configuration.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

assert_contains() {
  local output="$1"
  local expected="$2"
  if [[ "$output" != *"$expected"* ]]; then
    echo "Expected output to contain: $expected" >&2
    echo "$output" >&2
    exit 1
  fi
}

custom_dir="$(mktemp -d)"
trap 'rm -rf "$custom_dir"' EXIT

offset_file="$custom_dir/offset.env"
cat > "$offset_file" <<'EOF'
NEXT_PUBLIC_SUPABASE_URL=https://custom.example.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=custom-anon-key
SUPABASE_SERVICE_KEY=custom-service-key
EOF

offset_config="$("$ROOT/start.sh" config --env-file "$offset_file" --port-offset 20)"
assert_contains "$offset_config" "Frontend host port: 3020"
assert_contains "$offset_config" "Backend host port: 8020"
assert_contains "$offset_config" "Voice WebSocket host port: 7880"
assert_contains "$offset_config" "OTEL HTTP host port: 4338"
assert_contains "$offset_config" "Compose project: 247ai-custom-p20"

custom_file="$custom_dir/custom.env"
cat > "$custom_file" <<'EOF'
NEXT_PUBLIC_SUPABASE_URL=https://custom.example.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=custom-anon-key
SUPABASE_SERVICE_KEY=custom-service-key
PORT_OFFSET=7
HOST_BACKEND_PORT=9100
EOF

custom_config="$("$ROOT/start.sh" config --env-file "$custom_file")"
assert_contains "$custom_config" "Frontend host port: 3007"
assert_contains "$custom_config" "Backend host port: 9100"
assert_contains "$custom_config" "Voice WebSocket host port: 7867"
assert_contains "$custom_config" "Compose project: 247ai-custom-p7"

echo "Port configuration tests passed."
