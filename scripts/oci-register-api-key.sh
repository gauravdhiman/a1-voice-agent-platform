#!/usr/bin/env bash
# Register the local OCI API public key with your Oracle Cloud user account.
#
# Prefer browser session auth for local deploys (no API key upload needed):
#   oci session authenticate --region us-ashburn-1
#   source scripts/oci-env.sh
#   oci iam region list
#
# API key path (for CI): paste ~/.oci/oci_api_key_public.pem in OCI Console →
# User Settings → API Keys → Add API Key, then use default api_key auth.
set -euo pipefail

PUBLIC_KEY="${HOME}/.oci/oci_api_key_public.pem"

if [[ ! -f "${PUBLIC_KEY}" ]]; then
  echo "Missing ${PUBLIC_KEY}. Run: oci setup config"
  exit 1
fi

echo "=== OCI API key registration (one-time, for CI/automation) ==="
echo ""
echo "1. Open: https://cloud.oracle.com/ → Profile → User Settings"
echo "2. Resources → API Keys → Add API Key → Paste public key"
echo "3. Paste the key below:"
echo ""
cat "${PUBLIC_KEY}"
echo ""
echo "4. Verify: oci iam region list"
