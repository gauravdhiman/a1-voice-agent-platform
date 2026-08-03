"""Tests for the per-org provider key resolver (Phase 3).

The resolver is pure-Python: it pairs a ``SpeechConfig`` with an organization's
encrypted ``provider_credentials`` blob and the platform env vars to produce the
``api_keys`` map the speech-provider factory expects. It must:

- derive the *needed* providers from the config (realtime -> google; pipeline ->
  each stage's provider, with ``livekit_inference`` mapped to ``livekit``);
- prefer the org's decrypted key unless ``use_platform_credits``;
- fall back to the platform env var;
- **omit** a provider when neither org nor env has it (the registry's guard
  raises the clear error — no new error path here);
- inject ``api_keys["livekit"]`` (a nested ``{api_key, api_secret}`` dict) ONLY
  when the preset actually uses a LiveKit Inference stage;
- read Google from the decrypted ``provider_credentials`` blob, NOT the legacy
  plaintext ``google_api_key`` column.
"""

import os
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from shared.voice_agents.key_resolver import resolve_api_keys
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
    """A fake org carrying only an encrypted provider_credentials blob.

    Note: no ``google_api_key`` attribute — the resolver must NOT read the
    legacy plaintext column.
    """
    return SimpleNamespace(provider_credentials="encrypted-blob"), creds


@pytest.fixture
def patch_decrypt():
    """Patch decrypt_data inside key_resolver to return a controlled creds dict."""
    with patch("shared.voice_agents.key_resolver.decrypt_data") as m:
        yield m


@pytest.fixture
def clean_env(monkeypatch):
    """Strip every provider env var so tests are deterministic."""
    for var in (
        "GEMINI_API_KEY",
        "DEEPGRAM_API_KEY",
        "OPENAI_API_KEY",
        "CARTESIA_API_KEY",
        "CEREBRAS_API_KEY",
        "OPENROUTER_API_KEY",
        "FISH_API_KEY",
        "LIVEKIT_API_KEY",
        "LIVEKIT_API_SECRET",
    ):
        monkeypatch.delenv(var, raising=False)
    yield monkeypatch


class TestKeyResolver:
    """Test cases for resolve_api_keys."""

    def test_realtime_uses_platform_google_env(self, patch_decrypt, clean_env):
        """Realtime config with no org key resolves google from the platform env."""
        clean_env.setenv("GEMINI_API_KEY", "plat-gemini")
        api_keys = resolve_api_keys(_realtime(), org=None)
        assert api_keys == {"google": "plat-gemini"}

    def test_realtime_org_google_wins_over_env(self, patch_decrypt, clean_env):
        """Org's decrypted google key is preferred over the platform env."""
        clean_env.setenv("GEMINI_API_KEY", "plat-gemini")
        org, creds = _org({"google": "org-gemini"})
        patch_decrypt.return_value = creds
        api_keys = resolve_api_keys(_realtime(), org=org)
        assert api_keys == {"google": "org-gemini"}

    def test_realtime_use_platform_credits_ignores_org(self, patch_decrypt, clean_env):
        """use_platform_credits=True forces the platform env even when org has a key."""
        clean_env.setenv("GEMINI_API_KEY", "plat-gemini")
        org, creds = _org({"google": "org-gemini"})
        patch_decrypt.return_value = creds
        api_keys = resolve_api_keys(_realtime(), org=org, use_platform_credits=True)
        assert api_keys == {"google": "plat-gemini"}

    def test_pipeline_direct_only_no_livekit(self, patch_decrypt, clean_env):
        """An all-direct pipeline never injects a livekit entry."""
        clean_env.setenv("DEEPGRAM_API_KEY", "dg")
        clean_env.setenv("OPENAI_API_KEY", "oa")
        clean_env.setenv("CARTESIA_API_KEY", "ca")
        api_keys = resolve_api_keys(_pipeline(), org=None)
        assert api_keys == {"deepgram": "dg", "openai": "oa", "cartesia": "ca"}
        assert "livekit" not in api_keys

    def test_pipeline_openrouter_and_fish_keys(self, patch_decrypt, clean_env):
        """OpenRouter LLM and Fish Audio TTS resolve from platform env keys."""
        clean_env.setenv("DEEPGRAM_API_KEY", "dg")
        clean_env.setenv("OPENROUTER_API_KEY", "or")
        clean_env.setenv("FISH_API_KEY", "fish")
        cfg = _pipeline(llm="openrouter", tts="fish")
        api_keys = resolve_api_keys(cfg, org=None)
        assert api_keys == {
            "deepgram": "dg",
            "openrouter": "or",
            "fish": "fish",
        }
        assert "openai" not in api_keys
        assert "cartesia" not in api_keys

    def test_pipeline_with_inference_stage_injects_livekit(
        self, patch_decrypt, clean_env
    ):
        """A pipeline with one livekit_inference stage injects the nested livekit dict."""
        clean_env.setenv("DEEPGRAM_API_KEY", "dg")
        clean_env.setenv("OPENAI_API_KEY", "oa")
        clean_env.setenv("CARTESIA_API_KEY", "ca")
        clean_env.setenv("LIVEKIT_API_KEY", "lk-key")
        clean_env.setenv("LIVEKIT_API_SECRET", "lk-secret")
        cfg = _pipeline(stt="livekit_inference")
        api_keys = resolve_api_keys(cfg, org=None)
        assert api_keys["livekit"] == {"api_key": "lk-key", "api_secret": "lk-secret"}
        assert api_keys["openai"] == "oa"
        assert api_keys["cartesia"] == "ca"
        # deepgram was replaced by inference -> not needed
        assert "deepgram" not in api_keys

    def test_pipeline_inference_org_livekit_wins(self, patch_decrypt, clean_env):
        """Org's livekit credentials override the platform env."""
        clean_env.setenv("LIVEKIT_API_KEY", "plat-lk")
        clean_env.setenv("LIVEKIT_API_SECRET", "plat-lks")
        clean_env.setenv("OPENAI_API_KEY", "oa")
        clean_env.setenv("CARTESIA_API_KEY", "ca")
        org, creds = _org({"livekit": {"api_key": "org-lk", "api_secret": "org-lks"}})
        patch_decrypt.return_value = creds
        cfg = _pipeline(stt="livekit_inference")
        api_keys = resolve_api_keys(cfg, org=org)
        assert api_keys["livekit"] == {"api_key": "org-lk", "api_secret": "org-lks"}

    def test_missing_provider_omitted_not_raised(self, patch_decrypt, clean_env):
        """A provider with no org key and no env var is omitted — no exception."""
        # Only OPENAI set; deepgram + cartesia have nothing.
        clean_env.setenv("OPENAI_API_KEY", "oa")
        api_keys = resolve_api_keys(_pipeline(), org=None)
        assert api_keys == {"openai": "oa"}
        assert "deepgram" not in api_keys
        assert "cartesia" not in api_keys

    def test_livekit_value_is_nested_dict(self, patch_decrypt, clean_env):
        """The livekit entry is a dict with api_key/api_secret, not a string."""
        clean_env.setenv("LIVEKIT_API_KEY", "lk-key")
        clean_env.setenv("LIVEKIT_API_SECRET", "lk-secret")
        clean_env.setenv("OPENAI_API_KEY", "oa")
        clean_env.setenv("CARTESIA_API_KEY", "ca")
        cfg = _pipeline(llm="livekit_inference")
        api_keys = resolve_api_keys(cfg, org=None)
        assert isinstance(api_keys["livekit"], dict)
        assert set(api_keys["livekit"].keys()) == {"api_key", "api_secret"}

    def test_google_read_from_decrypted_blob_not_plaintext_column(
        self, patch_decrypt, clean_env
    ):
        """Google comes from provider_credentials['google'], never google_api_key.

        The fake org has NO ``google_api_key`` attribute; if the resolver tried to
        read it, getattr would return None and the test would fail to find the key.
        """
        clean_env.delenv("GEMINI_API_KEY", raising=False)
        org, creds = _org({"google": "org-gemini-from-blob"})
        patch_decrypt.return_value = creds
        api_keys = resolve_api_keys(_realtime(), org=org)
        assert api_keys == {"google": "org-gemini-from-blob"}
        # Sanity: the org really has no plaintext attribute to fall back on.
        assert not hasattr(org, "google_api_key")

    def test_use_platform_credits_forces_env_on_pipeline(
        self, patch_decrypt, clean_env
    ):
        """use_platform_credits ignores org creds across all pipeline providers."""
        clean_env.setenv("DEEPGRAM_API_KEY", "plat-dg")
        clean_env.setenv("OPENAI_API_KEY", "plat-oa")
        clean_env.setenv("CARTESIA_API_KEY", "plat-ca")
        org, creds = _org(
            {"deepgram": "org-dg", "openai": "org-oa", "cartesia": "org-ca"}
        )
        patch_decrypt.return_value = creds
        api_keys = resolve_api_keys(_pipeline(), org=org, use_platform_credits=True)
        assert api_keys == {
            "deepgram": "plat-dg",
            "openai": "plat-oa",
            "cartesia": "plat-ca",
        }

    def test_inference_with_no_livekit_anywhere_omitted(self, patch_decrypt, clean_env):
        """No livekit env and no org livekit -> livekit omitted (no raise)."""
        clean_env.setenv("OPENAI_API_KEY", "oa")
        clean_env.setenv("CARTESIA_API_KEY", "ca")
        cfg = _pipeline(stt="livekit_inference")
        api_keys = resolve_api_keys(cfg, org=None)
        assert "livekit" not in api_keys
        # direct stages still resolve
        assert api_keys == {"openai": "oa", "cartesia": "ca"}

    def test_unknown_provider_ignored(self, patch_decrypt, clean_env):
        """A provider with no env mapping (e.g. a local adapter) is silently ignored."""
        cfg = _pipeline(stt="silero", llm="openai", tts="cartesia")
        clean_env.setenv("OPENAI_API_KEY", "oa")
        clean_env.setenv("CARTESIA_API_KEY", "ca")
        api_keys = resolve_api_keys(cfg, org=None)
        assert api_keys == {"openai": "oa", "cartesia": "ca"}
        assert "silero" not in api_keys

    def test_decrypt_failure_yields_empty_creds(self, patch_decrypt, clean_env):
        """A decryption error falls back to no org creds (env still works)."""
        clean_env.setenv("GEMINI_API_KEY", "plat-gemini")
        org, _creds = _org({})
        patch_decrypt.side_effect = ValueError("bad key")
        api_keys = resolve_api_keys(_realtime(), org=org)
        assert api_keys == {"google": "plat-gemini"}


class TestKeyResolverEdgeBranches:
    """Cover the defensive branches (unsupported config, empty org blob)."""

    def test_unsupported_speech_config_raises_type_error(self, clean_env):
        """A non-Realtime/non-Pipeline config raises TypeError (fail-fast)."""
        with pytest.raises(TypeError):
            resolve_api_keys(speech_config="not-a-config", org=None)

    def test_org_with_empty_blob_treated_as_no_creds(self, patch_decrypt, clean_env):
        """An org whose provider_credentials is None/empty yields no org creds.

        The resolver must not call decrypt_data on a falsy blob; the env
        fallback still applies.
        """
        monkeypatch_env = clean_env
        monkeypatch_env.setenv("GEMINI_API_KEY", "ENV_GEM")
        org = SimpleNamespace(provider_credentials=None)
        keys = resolve_api_keys(speech_config=_realtime(), org=org)
        assert keys == {"google": "ENV_GEM"}
        patch_decrypt.assert_not_called()
