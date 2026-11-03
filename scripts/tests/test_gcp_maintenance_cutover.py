"""External maintenance deployments must not start without a prepared cutover."""

import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "deploy/gcp-deploy.sh"


@pytest.mark.parametrize(
    "mode,environment,worker_ok,scheduler_state,expected",
    [
        ("in_process", "production", False, "", 0),
        ("", "production", False, "", 1),
        ("", "staging", False, "", 0),
        ("external", "staging", False, "PAUSED", 1),
        ("external", "production", True, "ENABLED", 1),
        ("external", "production", True, "PAUSED", 0),
    ],
)
def test_cutover_requires_worker_and_paused_scheduler(
    mode, environment, worker_ok, scheduler_state, expected
):
    source = SCRIPT.read_text()
    function = (
        "validate_external_maintenance_cutover() {"
        + source.split("validate_external_maintenance_cutover() {", 1)[1].split(
            "\n}\n", 1
        )[0]
        + "\n}\n"
    )
    shell = f"""
PROJECT_ID=test-project
REGION=us-central1
read_env() {{
  if [[ "$1" == ENVIRONMENT ]]; then printf '%s' "$TEST_ENVIRONMENT";
  else printf '%s' "$TEST_MODE"; fi
}}
gcloud() {{
  if [[ "$1" == run ]]; then [[ "$TEST_WORKER_OK" == 1 ]];
  else printf '%s' "$TEST_SCHEDULER_STATE"; fi
}}
{function}
validate_external_maintenance_cutover
"""
    import os

    env = dict(
        os.environ,
        TEST_MODE=mode,
        TEST_ENVIRONMENT=environment,
        TEST_WORKER_OK=str(int(worker_ok)),
        TEST_SCHEDULER_STATE=scheduler_state,
    )
    result = subprocess.run(["bash", "-c", shell], env=env, capture_output=True)
    assert result.returncode == expected
