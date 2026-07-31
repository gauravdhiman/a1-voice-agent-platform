"""Tests for preset readiness (org-scoped voice profile availability).

Readiness is True when every provider a preset's SpeechConfig requires is
resolvable via the same path as ``resolve_api_keys`` (org credentials, platform
env fallback, or ``use_platform_credits``). Provider names are never exposed to
org-facing APIs — only the boolean result is surfaced.
"""

import os
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


def _realtime() -> RealtimeSpeechConfig:
    return RealtimeSpeechConfig()


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
    return SimpleNamespace(provider_credentials="encrypted-blob"), creds


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
        "LIVEKIT_API_KEY",
        "LIVEKIT_API_SECRET",
    ):
        monkeypatch.delenv(var, raising=False)
    yield monkeypatch


class TestIsPresetReady:
    """Unit tests for :func:`is_preset_ready`."""

    def test_realtime_ready_when_org_has_google(
        self, patch_decrypt, clean_env
    ):
        org, creds = _org({"google": "g-key"})
        patch_decrypt.return_value = creds
        assert is_preset_ready(_realtime(), org, use_platform_credits=False) is True

    def test_realtime_not_ready_when_no_keys_anywhere(
        self, patch_decrypt, clean_env
    ):
        org, creds = _org({})
        patch_decrypt.return_value = creds
        assert is_preset_ready(_realtime(), org, use_platform_credits=False) is False

    def test_realtime_ready_from_platform_env(
        self, patch_decrypt, clean_env
    ):
        org, creds = _org({})
        patch_decrypt.return_value = creds
        clean_env.setenv("GEMINI_API_KEY", "platform-g")
        assert is_preset_ready(_realtime(), org, use_platform_credits=False) is True

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

    def test_pipeline_ready_when_all_stage_keys_present(
        self, patch_decrypt, clean_env
    ):
        org, creds = _org(
            {"deepgram": "d", "openai": "o", "cartesia": "c"}
        )
        patch_decrypt.return_value = creds
        assert is_preset_ready(_pipeline(), org, use_platform_credits=False) is True

    def test_pipeline_not_ready_when_one_stage_missing(
        self, patch_decrypt, clean_env
    ):
        org, creds = _org({"deepgram": "d", "openai": "o"})
        patch_decrypt.return_value = creds
        assert is_preset_ready(_pipeline(), org, use_platform_credits=False) is False

    def test_use_platform_credits_ignores_org_and_uses_env(
        self, patch_decrypt, clean_env
    ):
        org, creds = _org({"google": "org-g"})
        patch_decrypt.return_value = creds
        clean_env.setenv("GEMINI_API_KEY", "platform-g")
        assert (
            is_preset_ready(_realtime(), org, use_platform_credits=True) is True
        )

    def test_livekit_inference_requires_both_api_key_and_secret(
        self, patch_decrypt, clean_env
    ):
        pipeline = _pipeline(stt="livekit_inference", llm="openai", tts="cartesia")
        org, creds = _org(
            {
                "livekit": {"api_key": "lk"},
                "openai": "o",
                "cartesia": "c",
            }
        )
        patch_decrypt.return_value = creds
        assert is_preset_ready(pipeline, org, use_platform_credits=False) is False

        creds["livekit"]["api_secret"] = "secret"
        patch_decrypt.return_value = creds
        assert is_preset_ready(pipeline, org, use_platform_credits=False) is True
