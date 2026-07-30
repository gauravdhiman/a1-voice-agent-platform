"""Per-org provider key resolver for the modular voice engine (Phase 3).

The resolver is the seam between a preset's ``SpeechConfig`` (which providers an
agent's engine needs) and the credentials those providers run on. It produces the
``api_keys`` map the speech-provider factory
(:mod:`worker.src.speech_providers.registry`) already expects:

- ``realtime`` engine -> ``{"google": <key>}``
- ``pipeline`` engine -> one entry per stage provider, e.g.
  ``{"deepgram": ..., "openai": ..., "cartesia": ...}``, plus a nested
  ``{"livekit": {"api_key": ..., "api_secret": ...}}`` **only when a stage uses
  LiveKit Inference** (``provider == "livekit_inference"``).

Resolution priority per provider (mirrors the existing Google-key logic in
``worker.py``, generalized to every provider):

1. If ``use_platform_credits`` is True -> always the platform env var (org creds
   ignored).
2. Else if the org's decrypted ``provider_credentials`` blob has the key -> the
   org key (BYO — billing goes to the tenant's own provider account).
3. Else -> the platform env var (fallback).
4. Else -> **omit** the provider. The registry's existing per-provider guard then
   raises a clear ``ValueError`` naming the provider, preserving the current
   fail-fast behavior — the resolver introduces no new error path.

All org provider keys — including the previously-plaintext ``google_api_key`` —
live in one Fernet-encrypted ``organizations.provider_credentials`` JSON blob
(:mod:`shared.common.security` ``encrypt_data``/``decrypt_data``). The resolver
decrypts it once per call and reads ``creds["google"]`` etc.; it NEVER reads the
legacy plaintext ``google_api_key`` column.

This module is pure-Python (no LiveKit import) so it is safe to import in both the
backend venv and the worker, and unit-testable without a network.
"""

import logging
import os
from typing import Any, Optional

from shared.common.security import decrypt_data
from shared.voice_agents.speech_config import (  # noqa: F401  (re-exported for callers)
    PipelineSpeechConfig,
    RealtimeSpeechConfig,
    SpeechConfig,
)

logger = logging.getLogger(__name__)

# Platform env var name for each direct (string-valued) provider. Providers not
# listed here (e.g. local adapters like "silero") carry no API key and are
# silently ignored by the resolver.
_PLATFORM_ENV: dict[str, str] = {
    "google": "GEMINI_API_KEY",
    "deepgram": "DEEPGRAM_API_KEY",
    "openai": "OPENAI_API_KEY",
    "cartesia": "CARTESIA_API_KEY",
    "cerebras": "CEREBRAS_API_KEY",
}

# LiveKit Inference dispatch key -> the api_keys entry name. Inference shares one
# LiveKit Cloud auth (api_key + api_secret) across STT/LLM/TTS, so all
# ``livekit_inference`` stages collapse into a single ``livekit`` entry.
_LIVEKIT_INFERENCE_DISPATCH = "livekit_inference"
_LIVEKIT_KEY = "livekit"


def _providers_needed(speech_config: SpeechConfig) -> set[str]:
    """Return the set of api_keys entries the config requires.

    Args:
        speech_config: A validated RealtimeSpeechConfig or PipelineSpeechConfig.

    Returns:
        A set of provider keys: ``{"google"}`` for realtime, or the per-stage
        providers for pipeline (with ``livekit_inference`` mapped to
        ``livekit``). Providers without an env mapping (e.g. ``silero``) are
        excluded — they need no key.

    Raises:
        TypeError: If ``speech_config`` is neither realtime nor pipeline config.
    """
    if isinstance(speech_config, RealtimeSpeechConfig):
        return {"google"}
    if isinstance(speech_config, PipelineSpeechConfig):
        needed: set[str] = set()
        for stage in (speech_config.stt, speech_config.llm, speech_config.tts):
            provider = stage.provider
            if provider == _LIVEKIT_INFERENCE_DISPATCH:
                needed.add(_LIVEKIT_KEY)
            elif provider in _PLATFORM_ENV:
                needed.add(provider)
            # Unknown/local providers (silero, future adapters) carry no key.
        return needed
    raise TypeError(
        f"Unsupported speech_config type: {type(speech_config)!r} "
        "(expected RealtimeSpeechConfig or PipelineSpeechConfig)"
    )


def _org_credentials(org: Optional[Any]) -> dict[str, Any]:
    """Decrypt the org's provider_credentials blob into a plain dict.

    Args:
        org: An organization-like object exposing ``provider_credentials`` (the
            encrypted TEXT blob), or ``None`` for "no org / legacy".

    Returns:
        The decrypted credentials dict (e.g.
        ``{"google": ..., "livekit": {"api_key": ..., "api_secret": ...}}``),
        or ``{}`` if there is no org, no blob, or decryption fails (a decryption
        failure is logged and treated as no org creds — the env fallback still
        applies, so a live call degrades rather than crashing).
    """
    if org is None:
        return {}
    blob = getattr(org, "provider_credentials", None)
    if not blob:
        return {}
    try:
        creds = decrypt_data(blob)
    except Exception as e:  # pragma: no cover - defensive, logged
        logger.error(
            "Failed to decrypt provider_credentials for org %s: %s",
            getattr(org, "id", "<unknown>"),
            e,
            exc_info=True,
        )
        return {}
    return creds if isinstance(creds, dict) else {}


def _resolve_livekit(
    creds: dict[str, Any], use_platform_credits: bool
) -> Optional[dict[str, str]]:
    """Resolve the nested ``{api_key, api_secret}`` LiveKit credential.

    Org values win unless ``use_platform_credits``; missing sub-keys are filled
    from the platform env (``LIVEKIT_API_KEY`` / ``LIVEKIT_API_SECRET``) so a
    partial org config still works.

    Args:
        creds: The decrypted org credentials dict.
        use_platform_credits: When True, ignore org creds and use env only.

    Returns:
        The ``{"api_key": ..., "api_secret": ...}`` dict if at least one of
        api_key/api_secret is resolvable, else ``None`` (caller omits the entry).
    """
    resolved: dict[str, str] = {}
    if not use_platform_credits:
        org_lk = creds.get(_LIVEKIT_KEY)
        if isinstance(org_lk, dict):
            for sub in ("api_key", "api_secret"):
                val = org_lk.get(sub)
                if val:
                    resolved[sub] = str(val)
    if not resolved.get("api_key"):
        env_k = os.environ.get("LIVEKIT_API_KEY")
        if env_k:
            resolved["api_key"] = env_k
    if not resolved.get("api_secret"):
        env_s = os.environ.get("LIVEKIT_API_SECRET")
        if env_s:
            resolved["api_secret"] = env_s
    if resolved.get("api_key") or resolved.get("api_secret"):
        return resolved
    return None


def resolve_api_keys(
    speech_config: SpeechConfig,
    org: Optional[Any] = None,
    use_platform_credits: bool = False,
) -> dict[str, Any]:
    """Build the per-provider ``api_keys`` map for a speech config + org.

    See the module docstring for the full resolution priority. Only the providers
    the config actually needs appear in the result, so an org without a LiveKit
    key running an all-direct pipeline never touches ``livekit``, and a realtime
    agent gets just ``{"google": ...}``.

    Args:
        speech_config: The validated SpeechConfig (realtime or pipeline) loaded
            from the agent's preset, or the System Default preset row for legacy
            agents (``preset_id`` NULL).
        org: The organization the agent belongs to (must expose
            ``provider_credentials``), or ``None``.
        use_platform_credits: When True, always use platform env vars and ignore
            the org's own credentials (mirrors the existing per-agent toggle).

    Returns:
        The ``api_keys`` map. String providers map to their key string;
        ``livekit`` (only when an Inference stage is used) maps to a nested
        ``{"api_key": ..., "api_secret": ...}`` dict. Providers with no
        resolvable key are omitted.
    """
    needed = _providers_needed(speech_config)
    creds = _org_credentials(org) if not use_platform_credits else {}
    api_keys: dict[str, Any] = {}

    for provider in needed:
        if provider == _LIVEKIT_KEY:
            resolved = _resolve_livekit(creds, use_platform_credits)
            if resolved is not None:
                api_keys[_LIVEKIT_KEY] = resolved
            continue
        value: Optional[str] = None
        if not use_platform_credits:
            value = creds.get(provider)
        if not value:
            env_name = _PLATFORM_ENV.get(provider)
            if env_name:
                value = os.environ.get(env_name)
        if value:
            api_keys[provider] = value

    return api_keys


__all__ = ["resolve_api_keys"]
