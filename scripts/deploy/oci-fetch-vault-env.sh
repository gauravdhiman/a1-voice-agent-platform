#!/usr/bin/env bash
# Render the voice-ws dotenv file from OCI Vault using instance principals.
#
# The OCI VM must have the OCI CLI installed and a dynamic-group policy that
# grants read access only to the listed secret-bundle resources.  Secret values
# are never printed.  The manifest contains names only and is safe to transfer
# from the deployment runner.
set -euo pipefail

PUBLIC_ENV="${1:?usage: oci-fetch-vault-env.sh PUBLIC_ENV MANIFEST OUTPUT_ENV}"
MANIFEST="${2:?usage: oci-fetch-vault-env.sh PUBLIC_ENV MANIFEST OUTPUT_ENV}"
OUTPUT_ENV="${3:?usage: oci-fetch-vault-env.sh PUBLIC_ENV MANIFEST OUTPUT_ENV}"

[[ -f "$PUBLIC_ENV" ]] || { echo "Missing public env file: $PUBLIC_ENV" >&2; exit 1; }
[[ -f "$MANIFEST" ]] || { echo "Missing secret manifest: $MANIFEST" >&2; exit 1; }
OCI_CLI_BIN="${OCI_CLI_BIN:-}"
if [[ -z "$OCI_CLI_BIN" ]] && command -v oci >/dev/null 2>&1; then
  OCI_CLI_BIN="$(command -v oci)"
fi
if [[ -z "$OCI_CLI_BIN" ]]; then
  for candidate in \
    "$HOME/lib/oracle-cli/bin/oci" \
    "$HOME/bin/oci" \
    "$HOME/.local/bin/oci"; do
    if [[ -x "$candidate" ]]; then
      OCI_CLI_BIN="$candidate"
      break
    fi
  done
fi
if [[ "$OCI_CLI_BIN" == */* ]]; then
  oci_available="$( [[ -x "$OCI_CLI_BIN" ]] && echo true || echo false )"
else
  oci_available="$(command -v "$OCI_CLI_BIN" >/dev/null 2>&1 && echo true || echo false)"
fi
[[ "$oci_available" == true ]] || {
  echo "OCI CLI is required on the voice-ws VM for instance-principal secret retrieval." >&2
  exit 1
}
command -v base64 >/dev/null 2>&1 || {
  echo "base64 is required on the voice-ws VM." >&2
  exit 1
}

read_public_value() {
  local wanted="$1"
  awk -F= -v key="$wanted" '
    $1 == key {
      sub(/^[^=]*=/, "")
      if (length($0) >= 2 && substr($0, 1, 1) == substr($0, length($0), 1) &&
          (substr($0, 1, 1) == "\047" || substr($0, 1, 1) == "\042")) {
        print substr($0, 2, length($0) - 2)
      } else {
        print
      }
      exit
    }
  ' "$PUBLIC_ENV"
}

VAULT_ID="$(read_public_value OCI_VAULT_ID)"
[[ -n "$VAULT_ID" ]] || {
  echo "OCI_VAULT_ID is required in the public deployment config." >&2
  exit 1
}

umask 077
temporary_env="${OUTPUT_ENV}.tmp.$$"
decoded_secret="${OUTPUT_ENV}.secret.tmp.$$"
trap 'rm -f "$temporary_env" "$decoded_secret"' EXIT

# Copy only service configuration.  Vault identifiers are deployment metadata,
# not runtime application settings.
awk -F= '$1 != "OCI_VAULT_ID" && $1 != "OCI_SECRET_NAME_PREFIX" {print}' \
  "$PUBLIC_ENV" > "$temporary_env"

required_keys=(
  ENCRYPTION_KEY
  JWT_SECRET_KEY
  SUPABASE_SERVICE_KEY
  GEMINI_API_KEY
)

is_required() {
  local candidate="$1"
  local key
  for key in "${required_keys[@]}"; do
    [[ "$key" == "$candidate" ]] && return 0
  done
  return 1
}

while IFS='=' read -r key secret_name; do
  [[ -n "$key" && -n "$secret_name" ]] || continue

  encoded=""
  if ! encoded="$(
    "$OCI_CLI_BIN" secrets secret-bundle get-secret-bundle-by-name \
      --auth instance_principal \
      --vault-id "$VAULT_ID" \
      --secret-name "$secret_name" \
      --stage CURRENT \
      --query 'data."secret-bundle-content".content' \
      --raw-output 2>/dev/null
  )"; then
    if is_required "$key"; then
      echo "Required OCI Vault secret is unavailable: $key" >&2
      exit 1
    fi
    echo "Optional OCI Vault secret is unavailable; continuing: $key" >&2
    continue
  fi

  if ! printf '%s' "$encoded" | base64 --decode > "$decoded_secret"; then
    echo "OCI Vault returned invalid base64 content: $key" >&2
    exit 1
  fi
  line_count="$(wc -l < "$decoded_secret" | tr -d '[:space:]')"
  if [[ "$line_count" != "0" ]] || LC_ALL=C grep -q $'\r' "$decoded_secret"; then
    echo "OCI Vault secret contains a newline and cannot be used as an env value: $key" >&2
    exit 1
  fi
  value="$(<"$decoded_secret")"
  if [[ -z "$value" ]]; then
    if is_required "$key"; then
      echo "Required OCI Vault secret is empty: $key" >&2
      exit 1
    fi
    continue
  fi
  printf '%s=%s\n' "$key" "$value" >> "$temporary_env"
  : > "$decoded_secret"
done < "$MANIFEST"

mv -f "$temporary_env" "$OUTPUT_ENV"
chmod 600 "$OUTPUT_ENV"
trap - EXIT
echo "Rendered voice-ws environment from OCI Vault."
