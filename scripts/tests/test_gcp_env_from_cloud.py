"""Regression tests for service environment generation during deployment."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "deploy" / "gcp-env-from-cloud.py"
MODULE_SPEC = importlib.util.spec_from_file_location(
    "gcp_env_from_cloud",
    SCRIPT_PATH,
)
assert MODULE_SPEC and MODULE_SPEC.loader
gcp_env = importlib.util.module_from_spec(MODULE_SPEC)
MODULE_SPEC.loader.exec_module(gcp_env)

RENDER_SCRIPT_PATH = (
    Path(__file__).resolve().parents[1] / "deploy" / "render-gcp-env.py"
)
RENDER_MODULE_SPEC = importlib.util.spec_from_file_location(
    "render_gcp_env",
    RENDER_SCRIPT_PATH,
)
assert RENDER_MODULE_SPEC and RENDER_MODULE_SPEC.loader
render_gcp_env = importlib.util.module_from_spec(RENDER_MODULE_SPEC)
RENDER_MODULE_SPEC.loader.exec_module(render_gcp_env)


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

ENCRYPTION_ENVIRONMENT_KEYS = {
    "ENCRYPTION_KEY",
    "ENCRYPTION_KEY_FALLBACKS",
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

    def test_backend_and_worker_allow_credential_encryption_configuration(
        self,
    ) -> None:
        """Every server-side runtime must receive the Fernet keyring."""
        self.assertTrue(
            ENCRYPTION_ENVIRONMENT_KEYS <= gcp_env.BACKEND_KEYS,
            "backend deployment allowlist is missing encryption variables",
        )
        self.assertTrue(
            ENCRYPTION_ENVIRONMENT_KEYS <= gcp_env.WORKER_KEYS,
            "voice-ws deployment allowlist is missing encryption variables",
        )

    def test_service_allowlists_cover_every_managed_secret_for_that_runtime(
        self,
    ) -> None:
        """A newly classified secret cannot be silently omitted at deploy time."""
        from secret_config import BACKEND_SECRET_KEYS, WORKER_SECRET_KEYS

        self.assertTrue(BACKEND_SECRET_KEYS <= gcp_env.BACKEND_KEYS)
        self.assertTrue(WORKER_SECRET_KEYS <= gcp_env.WORKER_KEYS)

    def test_tinyfish_secret_is_backend_only(self) -> None:
        """Website scraping credentials are only available to backend code."""
        from secret_config import BACKEND_SECRET_KEYS, WORKER_SECRET_KEYS

        self.assertIn("TINYFISH_API_KEY", BACKEND_SECRET_KEYS)
        self.assertNotIn("TINYFISH_API_KEY", WORKER_SECRET_KEYS)

        repository_root = Path(__file__).resolve().parents[2]
        compose_services = {
            "docker-compose.yml": ("frontend", "voice-ws"),
            "docker-compose.dev.yml": ("frontend-dev", "voice-ws-dev"),
        }
        for compose_name, services in compose_services.items():
            composition = yaml.safe_load((repository_root / compose_name).read_text())
            for service in services:
                environment = composition["services"][service]["environment"]
                self.assertIn("TINYFISH_API_KEY=", environment)

    def test_frontend_only_anon_key_is_not_in_server_secret_refs(self) -> None:
        """The browser-only Supabase anon key is not injected into Cloud Run backend."""
        self.assertNotIn("NEXT_PUBLIC_SUPABASE_ANON_KEY", gcp_env.BACKEND_KEYS)

    def test_generated_yaml_contains_credential_encryption_configuration(
        self,
    ) -> None:
        """Generated server env files must carry the encryption keyring."""
        source_env = {
            "ENCRYPTION_KEY": "current-fernet-key",
            "ENCRYPTION_KEY_FALLBACKS": "previous-fernet-key",
        }

        backend_yaml = gcp_env.to_yaml(source_env, gcp_env.BACKEND_KEYS)
        worker_yaml = gcp_env.to_yaml(source_env, gcp_env.WORKER_KEYS)

        for rendered in (backend_yaml, worker_yaml):
            for key, value in source_env.items():
                self.assertIn(f'{key}: "{value}"', rendered)

    def test_managed_secret_mode_omits_secret_values(self) -> None:
        """Cloud Run env YAML must not duplicate Secret Manager payloads."""
        rendered = gcp_env.to_yaml(
            {
                "APP_NAME": "24x7 AI",
                "ENCRYPTION_KEY": "do-not-render",
                "JWT_SECRET_KEY": "do-not-render-either",
            },
            {"APP_NAME", "ENCRYPTION_KEY", "JWT_SECRET_KEY"},
            "gcp",
        )
        self.assertIn('APP_NAME: "24x7 AI"', rendered)
        self.assertNotIn("do-not-render", rendered)

    def test_render_does_not_reactivate_omitted_optional_secrets(self) -> None:
        """Stale manager versions stay out unless config opts an integration in."""
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "config.env"
            output_path = Path(directory) / "rendered.env"
            config_path.write_text("APP_NAME=24x7 AI\nENCRYPTION_KEY=\n")
            requested: list[str] = []

            def fake_fetch(_project: str, secret_id: str) -> tuple[str, bool]:
                requested.append(secret_id)
                return "managed-value", True

            with patch.object(render_gcp_env, "_fetch_secret", side_effect=fake_fetch):
                fetched, _value_count = render_gcp_env.render(
                    config_path,
                    output_path,
                    "project",
                    "247ai-test",
                    {"JWT_SECRET_KEY"},
                )

            rendered = output_path.read_text()
            self.assertEqual(fetched, 2)
            self.assertIn("247ai-test-encryption-key", requested)
            self.assertIn("247ai-test-jwt-secret-key", requested)
            self.assertNotIn("247ai-test-openai-api-key", requested)
            self.assertIn("ENCRYPTION_KEY=managed-value", rendered)
            self.assertIn("JWT_SECRET_KEY=managed-value", rendered)
            self.assertEqual(output_path.stat().st_mode & 0o777, 0o600)

    def test_public_worker_render_contains_only_vault_metadata(self) -> None:
        """The OCI transfer manifest contains config, never secret values."""
        rendered = gcp_env.to_dotenv(
            {
                "ENVIRONMENT": "production",
                "OCI_VAULT_ID": "ocid1.vault.example",
                "OCI_SECRET_NAME_PREFIX": "247ai-production",
                "GEMINI_API_KEY": "do-not-render",
            },
            {"ENVIRONMENT", "GEMINI_API_KEY"},
            "public",
            public_worker=True,
        )
        self.assertIn("ENVIRONMENT='production'", rendered)
        self.assertIn("OCI_VAULT_ID='ocid1.vault.example'", rendered)
        self.assertNotIn("do-not-render", rendered)

    def test_secret_manifest_contains_names_only(self) -> None:
        """OCI bootstrap manifests derive stable names without payloads."""
        manifest = gcp_env.to_secret_manifest(
            "voice-ws",
            "247ai-production",
            {"ENCRYPTION_KEY": "", "GEMINI_API_KEY": ""},
        )
        self.assertIn("GEMINI_API_KEY=247ai-production-gemini-api-key", manifest)
        self.assertIn("ENCRYPTION_KEY=247ai-production-encryption-key", manifest)
        self.assertIn("JWT_SECRET_KEY=247ai-production-jwt-secret-key", manifest)
        self.assertNotIn("OPENAI_API_KEY=", manifest)
        self.assertNotIn("=your-", manifest)

    def test_generated_service_names_are_distinct(self) -> None:
        """Backend and voice traces must be separable in cloud backends."""
        source_env = {
            "OTEL_SERVICE_NAME": "shared-name",
            "OTEL_BACKEND_SERVICE_NAME": "247ai-backend-production",
            "OTEL_VOICE_WS_SERVICE_NAME": "247ai-voice-ws-production",
        }
        backend_yaml = gcp_env.to_yaml(
            {
                **source_env,
                "OTEL_SERVICE_NAME": source_env["OTEL_BACKEND_SERVICE_NAME"],
            },
            gcp_env.BACKEND_KEYS,
        )
        worker_yaml = gcp_env.to_yaml(
            {
                **source_env,
                "OTEL_SERVICE_NAME": source_env["OTEL_VOICE_WS_SERVICE_NAME"],
            },
            gcp_env.WORKER_KEYS,
        )
        self.assertIn('OTEL_SERVICE_NAME: "247ai-backend-production"', backend_yaml)
        self.assertIn('OTEL_SERVICE_NAME: "247ai-voice-ws-production"', worker_yaml)

    def test_generated_yaml_contains_bucket_scoped_r2_configuration(self) -> None:
        """Generated service YAML must carry non-empty R2 values unchanged."""
        source_env = {
            key: f"value-for-{key.lower()}" for key in RECORDING_ENVIRONMENT_KEYS
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

    def test_server_side_encryption_requires_current_key(self) -> None:
        """Server deployment must fail before starting without Fernet keying."""
        with self.assertRaisesRegex(ValueError, "ENCRYPTION_KEY"):
            gcp_env.validate_encryption_configuration({})

    def test_disabled_observability_is_allowed_for_staging(self) -> None:
        """Staging and local deployments remain opt-out by default."""
        gcp_env.validate_observability_configuration(
            {"ENVIRONMENT": "staging", "OTEL_ENABLED": "false"}
        )

    def test_env_parser_removes_matching_secret_quotes(self) -> None:
        """Deployment generation should follow normal dotenv quote semantics."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text(
                "OTEL_EXPORTER_OTLP_TRACES_HEADERS='Authorization=Basic a=b=='\n"
            )
            self.assertEqual(
                gcp_env.parse_env_file(path)["OTEL_EXPORTER_OTLP_TRACES_HEADERS"],
                "Authorization=Basic a=b==",
            )

    def test_enabled_observability_requires_all_signal_configuration(self) -> None:
        """A partial OTLP configuration must fail before an app is deployed."""
        with self.assertRaisesRegex(ValueError, "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT"):
            gcp_env.validate_observability_configuration(
                {"ENVIRONMENT": "production", "OTEL_ENABLED": "true"}
            )

    def test_production_observability_requires_https_and_non_placeholder_values(
        self,
    ) -> None:
        """Production telemetry cannot silently use plaintext or examples."""
        values = {
            "ENVIRONMENT": "production",
            "OTEL_ENABLED": "true",
        }
        for signal in ("TRACES", "METRICS", "LOGS"):
            values.update(
                {
                    f"OTEL_EXPORTER_OTLP_{signal}_ENDPOINT": (
                        f"http://telemetry.example/v1/{signal.lower()}"
                    ),
                    f"OTEL_EXPORTER_OTLP_{signal}_PROTOCOL": "http/protobuf",
                    f"OTEL_EXPORTER_OTLP_{signal}_HEADERS": "Authorization=Basic token",
                }
            )
        with self.assertRaisesRegex(ValueError, "HTTPS"):
            gcp_env.validate_observability_configuration(values)

        values["OTEL_EXPORTER_OTLP_TRACES_PROTOCOL"] = "grpc"
        with self.assertRaisesRegex(ValueError, "http/protobuf"):
            gcp_env.validate_observability_configuration(values)
        values["OTEL_EXPORTER_OTLP_TRACES_PROTOCOL"] = "http/protobuf"

        for signal in ("TRACES", "METRICS", "LOGS"):
            values[f"OTEL_EXPORTER_OTLP_{signal}_ENDPOINT"] = (
                f"https://telemetry.example/v1/{signal.lower()}"
            )
        values["OTEL_EXPORTER_OTLP_LOGS_HEADERS"] = "replace-with-header"
        with self.assertRaisesRegex(ValueError, "LOGS_HEADERS"):
            gcp_env.validate_observability_configuration(values)

    def test_cors_origins_is_emitted_as_valid_json_string(self) -> None:
        """Cloud Run must receive JSON for loosely formatted source lists."""
        for source_value in (
            '["https://www.247ai.live"]',
            "[https://www.247ai.live]",
        ):
            rendered = gcp_env.to_yaml(
                {"CORS_ORIGINS": source_value},
                {"CORS_ORIGINS"},
            )
            self.assertIn(
                "CORS_ORIGINS: '[\"https://www.247ai.live\"]'",
                rendered,
            )


if __name__ == "__main__":
    unittest.main()
