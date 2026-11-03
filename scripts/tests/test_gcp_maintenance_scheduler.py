"""Cloud Scheduler payload and secret-handling contracts."""

import importlib.util
from pathlib import Path
from unittest.mock import patch

import pytest

path = (
    Path(__file__).resolve().parents[1] / "deploy/gcp-create-maintenance-scheduler.py"
)
spec = importlib.util.spec_from_file_location("maintenance_scheduler", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_scheduler_uses_oidc_and_separate_secret_header():
    job = module.build_job(
        "test-project",
        "us-central1",
        "maintenance-tick",
        "https://maintenance-test.run.app",
        "scheduler@test-project.iam.gserviceaccount.com",
        "x" * 32,
    )
    assert job["schedule"] == "* * * * *"
    target = job["httpTarget"]
    assert target["uri"] == "https://maintenance-test.run.app/v1/tick"
    assert target["oidcToken"]["audience"] == "https://maintenance-test.run.app"
    assert target["headers"]["X-Maintenance-Key"] == "x" * 32


@pytest.mark.parametrize(
    "url",
    [
        "http://maintenance-test.run.app",
        "https://evil.example",
        "https://user:pass@x.run.app",
    ],
)
def test_scheduler_rejects_untrusted_url(url):
    with pytest.raises(ValueError):
        module.build_job(
            "project",
            "us-central1",
            "tick",
            url,
            "scheduler@project.iam.gserviceaccount.com",
            "x" * 32,
        )


def test_creation_failure_never_prints_provider_secrets(capsys):
    env = {
        "GCP_PROJECT_ID": "project",
        "GCP_REGION": "us-central1",
        "MAINTENANCE_SERVICE_URL": "https://worker.run.app",
        "MAINTENANCE_SCHEDULER_SERVICE_ACCOUNT": (
            "scheduler@project.iam.gserviceaccount.com"
        ),
        "MAINTENANCE_AUTH_SECRET_REF": "secret:1",
    }
    with patch.dict(module.os.environ, env, clear=True), patch.object(
        module, "gcloud_output", side_effect=RuntimeError("private credential")
    ):
        assert module.main() == 1
    assert "private credential" not in capsys.readouterr().err
