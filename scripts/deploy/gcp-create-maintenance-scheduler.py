#!/usr/bin/env python3
"""Create one private Cloud Scheduler job for a deployed maintenance service.

The scheduler stores its maintenance header as configuration: restrict job read
permissions. Credentials and API response bodies are never printed.
"""

import json
import os
import re
import subprocess
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen


def required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ValueError(f"{name} is required")
    return value


def build_job(
    project: str, region: str, job_id: str, url: str, identity: str, secret: str
) -> dict:
    """Build a minute-cadence job with OIDC and a separate application secret."""
    for value in (project, region, job_id):
        if not re.fullmatch(r"[a-z][a-z0-9-]{0,62}", value):
            raise ValueError("Invalid project, region, or job name")
    parsed = urlsplit(url)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or not parsed.hostname.endswith(".run.app")
        or parsed.path not in ("", "/")
        or parsed.username
        or parsed.password
        or parsed.port
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("Maintenance URL must be a Cloud Run service HTTPS URL")
    if not re.fullmatch(r"[a-z0-9-]+@[a-z0-9-]+\.iam\.gserviceaccount\.com", identity):
        raise ValueError("Scheduler identity must be a service account email")
    if len(secret) < 32 or not secret.isascii() or any(c.isspace() for c in secret):
        raise ValueError("Maintenance secret must contain 32 or more ASCII characters")
    base_url = url.rstrip("/")
    return {
        "name": f"projects/{project}/locations/{region}/jobs/{job_id}",
        "schedule": "* * * * *",
        "timeZone": "Etc/UTC",
        "attemptDeadline": "900s",
        "retryConfig": {"retryCount": 2, "minBackoffDuration": "30s"},
        "httpTarget": {
            "uri": f"{base_url}/v1/tick",
            "httpMethod": "POST",
            "headers": {"X-Maintenance-Key": secret},
            "oidcToken": {"serviceAccountEmail": identity, "audience": base_url},
        },
    }


def gcloud_output(args: list[str]) -> str:
    """Read gcloud output privately, reporting only a generic failure."""
    result = subprocess.run(["gcloud", *args], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError("Could not read Google credentials or secret")
    return result.stdout.strip()


def main() -> int:
    try:
        project = required("GCP_PROJECT_ID")
        region = required("GCP_REGION")
        job_id = os.environ.get("GCP_MAINTENANCE_SCHEDULER_JOB", "maintenance-tick")
        url = required("MAINTENANCE_SERVICE_URL")
        identity = required("MAINTENANCE_SCHEDULER_SERVICE_ACCOUNT")
        ref = required("MAINTENANCE_AUTH_SECRET_REF")
        if not re.fullmatch(r"[A-Za-z0-9_-]+:[0-9]+", ref):
            raise ValueError(
                "Maintenance secret reference must contain a numeric version"
            )
        secret_id, version = ref.split(":")
        secret = gcloud_output(
            [
                "secrets",
                "versions",
                "access",
                version,
                f"--secret={secret_id}",
                f"--project={project}",
            ]
        )
        job = build_job(project, region, job_id, url, identity, secret)
        access_token = gcloud_output(["auth", "print-access-token"])
        endpoint = (
            "https://cloudscheduler.googleapis.com/v1/projects/"
            f"{quote(project, safe='')}/locations/{quote(region, safe='')}/jobs"
        )
        request = Request(
            endpoint,
            data=json.dumps(job).encode(),
            method="POST",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
        )
        with urlopen(request, timeout=30) as response:
            if response.status not in (200, 201):
                raise RuntimeError("Scheduler did not confirm creation")
        print("Maintenance scheduler created; verify IAM and its first execution.")
        return 0
    except (ValueError, RuntimeError, OSError, HTTPError, URLError) as exc:
        # Provider response bodies or secret-bearing URLs must never reach logs.
        print(f"Scheduler creation failed ({type(exc).__name__}).", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
