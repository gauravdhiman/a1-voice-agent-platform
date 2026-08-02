#!/usr/bin/env bash
# Source before OCI deploy commands on a machine authenticated via:
#   oci session authenticate --region us-ashburn-1
#
# Example:
#   source scripts/oci-env.sh
#   oci iam region list
export OCI_CLI_CONFIG_FILE="${OCI_CLI_CONFIG_FILE:-${HOME}/.oci/config}"
export OCI_CLI_PROFILE="${OCI_CLI_PROFILE:-default}"
export OCI_CLI_AUTH="${OCI_CLI_AUTH:-security_token}"
