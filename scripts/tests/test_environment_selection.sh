#!/usr/bin/env bash
# Regression tests for the root environment-file selector used by start.sh.
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

local_config="$("$ROOT/start.sh" config --env local)"
assert_contains "$local_config" "Environment: local"
assert_contains "$local_config" "Env file: $ROOT/.env.local"
assert_contains "$local_config" "Supabase: http://127.0.0.1:54321"

staging_config="$("$ROOT/start.sh" config --env staging)"
assert_contains "$staging_config" "Environment: staging"
assert_contains "$staging_config" "Env file: $ROOT/.env.staging"
assert_contains "$staging_config" "Supabase: https://gdzwiwukcwbqohfwxxrx.supabase.co"

prefix_option_config="$("$ROOT/start.sh" --env staging config)"
assert_contains "$prefix_option_config" "Environment: staging"
assert_contains "$prefix_option_config" "Env file: $ROOT/.env.staging"

production_config="$("$ROOT/start.sh" config --env production)"
assert_contains "$production_config" "Environment: production"
assert_contains "$production_config" "Env file: $ROOT/.env.prod"
assert_contains "$production_config" "Supabase: https://zymiyfilulmtrmyyhvzw.supabase.co"

production_mode_config="$("$ROOT/start.sh" config prod)"
assert_contains "$production_mode_config" "Environment: production"
assert_contains "$production_mode_config" "Env file: $ROOT/.env.prod"

if [[ ! -f "$ROOT/.env.prod" ]]; then
  echo "Expected .env.prod to exist" >&2
  exit 1
fi

if [[ -e "$ROOT/.env.cloud" ]]; then
  echo "Legacy .env.cloud should not exist" >&2
  exit 1
fi

default_config="$("$ROOT/start.sh" config)"
assert_contains "$default_config" "Environment: local"
assert_contains "$default_config" "Env file: $ROOT/.env.local"

echo "Environment selection tests passed."
