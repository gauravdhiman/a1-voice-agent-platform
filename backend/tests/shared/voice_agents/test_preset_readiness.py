"""Tests for preset readiness (org-scoped voice profile availability).

Readiness is True when every provider a preset's SpeechConfig requires is
resolvable via the same path as ``resolve_api_keys`` (org credentials, platform
env fallback, or ``use_platform_credits``). Provider names are never exposed to
org-facing APIs — only the boolean result is surfaced.
"""

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from shared.voice_agents.key_resolver import is_preset_ready
from shared.voice_agents.speech_config import (
    LLMStageConfig,
    PipelineSpeechConfig,
    RealtimeSpeechConfig,
    STTStageConfig,
    TTSStageConfig,
)


def _realtime(provider: str = "google") -> RealtimeSpeechConfig:
    return RealtimeSpeechConfig(provider=provider)


def _pipeline(
    stt: str = "deepgram",
    llm: str = "openai",
    tts: str = "cartesia",
) -> PipelineSpeechConfig:
    return PipelineSpeechConfig(
        stt=STTStageConfig(provider=stt),
        llm=LLMStageConfig(provider=llm),
        tts=TTSStageConfig(provider=tts),
    )


def _org(creds: dict):
    # An empty credential map represents an unconfigured organization. A
    # non-empty blob with no decryptable payload is a different, fail-closed
    # state covered by the key-resolver tests.
    blob = "encrypted-blob" if creds else None
    return SimpleNamespace(provider_credentials=blob), creds


@pytest.fixture
def patch_decrypt():
    with patch("shared.voice_agents.key_resolver.decrypt_data") as m:
        yield m


@pytest.fixture
def clean_env(monkeypatch):
    for var in (
        "GEMINI_API_KEY",
        "DEEPGRAM_API_KEY",
        "OPENAI_API_KEY",
        "CARTESIA_API_KEY",
        "CEREBRAS_API_KEY",
        "OPENROUTER_API_KEY",
        "FISH_API_KEY",
    ):
        monkeypatch.delenv(var, raising=False)
    yield monkeypatch


class TestIsPresetReady:
    """Unit tests for :func:`is_preset_ready`."""

    def test_realtime_ready_when_org_has_google(self, patch_decrypt, clean_env):
        org, creds = _org({"google": "g-key"})
        patch_decrypt.return_value = creds
        assert is_preset_ready(_realtime(), org, use_platform_credits=False) is True

    def test_realtime_not_ready_when_no_keys_anywhere(self, patch_decrypt, clean_env):
        org, creds = _org({})
        patch_decrypt.return_value = creds
        assert is_preset_ready(_realtime(), org, use_platform_credits=False) is False

    def test_realtime_ready_from_platform_env(self, patch_decrypt, clean_env):
        org, creds = _org({})
        patch_decrypt.return_value = creds
        clean_env.setenv("GEMINI_API_KEY", "platform-g")
        assert is_preset_ready(_realtime(), org, use_platform_credits=False) is True

    def test_platform_preset_readiness_uses_platform_env_only(
        self, patch_decrypt, clean_env
    ):
        org, creds = _org({"google": "org-g"})
        patch_decrypt.return_value = creds
        clean_env.setenv("GEMINI_API_KEY", "platform-g")
        assert is_preset_ready(_realtime(), org, credential_source="platform") is True

    def test_platform_preset_readiness_uses_database_key_before_env(
        self, patch_decrypt, clean_env
    ):
        org, creds = _org({})
        patch_decrypt.return_value = creds

        assert (
            is_preset_ready(
                _realtime(),
                org,
                credential_source="platform",
                platform_credentials={"google": "database-g"},
            )
            is True
        )

    def test_organization_preset_readiness_requires_org_keys(
        self, patch_decrypt, clean_env
    ):
        org, creds = _org({})
        patch_decrypt.return_value = creds
        clean_env.setenv("GEMINI_API_KEY", "platform-g")
        assert (
            is_preset_ready(_realtime(), org, credential_source="organization") is False
        )

    def test_openai_realtime_ready_from_openai_platform_env(
        self, patch_decrypt, clean_env
    ):
        org, creds = _org({})
        patch_decrypt.return_value = creds
        clean_env.setenv("OPENAI_API_KEY", "platform-openai")
        assert (
            is_preset_ready(_realtime("openai"), org, use_platform_credits=False)
            is True
        )

    def test_realtime_not_ready_for_org_catalog_when_only_platform_env(
        self, patch_decrypt, clean_env
    ):
        """Org-facing catalog must not treat platform env as org setup."""
        org, creds = _org({})
        patch_decrypt.return_value = creds
        clean_env.setenv("GEMINI_API_KEY", "platform-g")
        assert (
            is_preset_ready(
                _realtime(),
                org,
                use_platform_credits=False,
                org_credentials_only=True,
            )
            is False
        )

    def test_realtime_ready_for_org_catalog_with_legacy_google_column(
        self, patch_decrypt, clean_env
    ):
        org = SimpleNamespace(
            provider_credentials=None,
            google_api_key="legacy-google-key",
        )
        assert (
            is_preset_ready(
                _realtime(),
                org,
                use_platform_credits=False,
                org_credentials_only=True,
            )
            is True
        )

    def test_pipeline_ready_when_all_stage_keys_present(self, patch_decrypt, clean_env):
        org, creds = _org({"deepgram": "d", "openai": "o", "cartesia": "c"})
        patch_decrypt.return_value = creds
        assert is_preset_ready(_pipeline(), org, use_platform_credits=False) is True

    def test_pipeline_not_ready_when_one_stage_missing(self, patch_decrypt, clean_env):
        org, creds = _org({"deepgram": "d", "openai": "o"})
        patch_decrypt.return_value = creds
        assert is_preset_ready(_pipeline(), org, use_platform_credits=False) is False

    def test_use_platform_credits_ignores_org_and_uses_env(
        self, patch_decrypt, clean_env
    ):
        org, creds = _org({"google": "org-g"})
        patch_decrypt.return_value = creds
        clean_env.setenv("GEMINI_API_KEY", "platform-g")
        assert is_preset_ready(_realtime(), org, use_platform_credits=True) is True

    def test_livekit_inference_stt_requires_deepgram_key(
        self, patch_decrypt, clean_env
    ):
        """Deprecated livekit_inference STT is ready when deepgram is configured."""
        pipeline = _pipeline(stt="livekit_inference", llm="openai", tts="cartesia")
        org, creds = _org({"openai": "o", "cartesia": "c"})
        patch_decrypt.return_value = creds
        assert is_preset_ready(pipeline, org, use_platform_credits=False) is False

        creds["deepgram"] = "d-key"
        patch_decrypt.return_value = creds
        assert is_preset_ready(pipeline, org, use_platform_credits=False) is True
