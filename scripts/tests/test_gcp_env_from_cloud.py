"""Regression tests for service environment generation during deployment."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1] / "deploy" / "gcp-env-from-cloud.py"
)
MODULE_SPEC = importlib.util.spec_from_file_location(
    "gcp_env_from_cloud",
    SCRIPT_PATH,
)
assert MODULE_SPEC and MODULE_SPEC.loader
gcp_env = importlib.util.module_from_spec(MODULE_SPEC)
MODULE_SPEC.loader.exec_module(gcp_env)


RECORDING_ENVIRONMENT_KEYS = {
    "VOICE_RECORDING_ENABLED",
    "VOICE_RECORDING_TEE",
    "RECORDING_STORAGE_BACKEND",
    "RECORDING_STORAGE_LOCAL_ROOT",
    "RECORDING_ENCRYPTION_MODE",
    "RECORDING_RETENTION_DAYS",
    "RECORDING_R2_ENDPOINT",
    "RECORDING_R2_BUCKET",
    "RECORDING_R2_ACCESS_KEY_ID",
    "RECORDING_R2_SECRET_ACCESS_KEY",
    "RECORDING_R2_PRESIGN_TTL_SECONDS",
}


class GcpEnvironmentGenerationTests(unittest.TestCase):
    """Ensure deployed services receive the complete recording configuration."""

    def test_backend_and_worker_allow_recording_configuration(self) -> None:
        """Both recording-producing and playback services need R2 settings."""
        self.assertTrue(
            RECORDING_ENVIRONMENT_KEYS <= gcp_env.BACKEND_KEYS,
            "backend deployment allowlist is missing recording variables",
        )
        self.assertTrue(
            RECORDING_ENVIRONMENT_KEYS <= gcp_env.WORKER_KEYS,
            "voice-ws deployment allowlist is missing recording variables",
        )

    def test_generated_yaml_contains_bucket_scoped_r2_configuration(self) -> None:
        """Generated service YAML must carry non-empty R2 values unchanged."""
        source_env = {
            key: f"value-for-{key.lower()}"
            for key in RECORDING_ENVIRONMENT_KEYS
        }

        backend_yaml = gcp_env.to_yaml(source_env, gcp_env.BACKEND_KEYS)
        worker_yaml = gcp_env.to_yaml(source_env, gcp_env.WORKER_KEYS)

        for rendered in (backend_yaml, worker_yaml):
            for key, value in source_env.items():
                self.assertIn(f'{key}: "{value}"', rendered)

    def test_enabled_r2_recording_requires_complete_credentials(self) -> None:
        """Deployment should fail clearly instead of silently disabling storage."""
        with self.assertRaisesRegex(ValueError, "RECORDING_R2_ENDPOINT"):
            gcp_env.validate_recording_configuration(
                {
                    "VOICE_RECORDING_ENABLED": "true",
                    "RECORDING_STORAGE_BACKEND": "r2",
                }
            )


if __name__ == "__main__":
    unittest.main()
