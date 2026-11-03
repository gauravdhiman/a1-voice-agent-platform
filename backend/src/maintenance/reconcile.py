"""Guarded operator recovery for a reviewed, held maintenance claim."""

import argparse
from uuid import UUID

from shared.config import supabase_config

from .jobs import maintenance_jobs


def main(argv=None, *, client=None) -> int:
    """Release one exact claim after explicit worker and provider verification."""
    parser = argparse.ArgumentParser(
        description=(
            "Release a reconciled maintenance claim; " "never use as a retry shortcut."
        )
    )
    parser.add_argument("--job", required=True)
    parser.add_argument("--claim", required=True)
    parser.add_argument("--worker-stopped", action="store_true")
    parser.add_argument("--provider-outcome-verified", action="store_true")
    args = parser.parse_args(argv)
    if args.job not in maintenance_jobs():
        try:
            prefix, value = args.job.split(":", 1)
            if prefix != "phone-org" or str(UUID(value)) != value:
                raise ValueError
        except ValueError:
            parser.error("Unknown maintenance job")
    if not (args.worker_stopped and args.provider_outcome_verified):
        parser.error("Both worker termination and provider outcome must be verified")
    client = client or supabase_config.service_client
    if client is None:
        raise RuntimeError("A service-role database client is required")
    response = client.rpc(
        "reconcile_maintenance_run", {"p_job": args.job, "p_claim": args.claim}
    ).execute()
    if response.data is not True:
        raise RuntimeError("The exact held claim was not reconciled")
    print("Maintenance claim reconciled; the scheduler can retry when due.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
