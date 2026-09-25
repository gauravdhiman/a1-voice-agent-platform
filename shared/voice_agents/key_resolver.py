"""Per-org provider key resolver for the modular voice engine (Phase 3).

The resolver is the seam between a preset's ``SpeechConfig`` (which providers an
agent's engine needs) and the credentials those providers run on. It produces the
``api_keys`` map the speech-provider factory expects:

- ``realtime`` engine -> the configured provider key, for example
  ``{"google": <key>}`` or ``{"openai": <key>}``
- ``pipeline`` engine -> one entry per direct stage provider, e.g.
  ``{"deepgram": ..., "openai": ..., "cartesia": ...}``.

Resolution priority per provider (mirrors the existing Google-key logic in
``worker.py``, generalized to every provider):

1. If ``use_platform_credits`` is True -> always the platform env var (org creds
   ignored).
2. Else if the org's decrypted ``provider_credentials`` blob has the key -> the
   org key (BYO — billing goes to the tenant's own provider account).
3. Else -> the platform env var (fallback), but only when the organization has
   no configured encrypted credential blob.
4. Else -> **omit** the provider. The registry's existing per-provider guard then
   raises a clear ``ValueError`` naming the provider, preserving the current
   fail-fast behavior — the resolver introduces no new error path.

If an organization has a non-empty encrypted blob that cannot be authenticated,
resolution fails closed and never falls back to a platform key. This prevents a
key-ring/configuration failure from silently charging the platform account.

All current org provider keys live in one Fernet-encrypted
``organizations.provider_credentials`` JSON blob (:mod:`shared.common.security`
``encrypt_data``/``decrypt_data``). During the staged rollout only, the
resolver retains a legacy ``google_api_key`` fallback for rows created by an
older application instance; the credential migration clears those values
before the compatibility column is removed in a later release.

This module is pure-Python (no LiveKit import) so it is safe to import in both the
backend venv and voice-ws, and unit-testable without a network.
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
    "openrouter": "OPENROUTER_API_KEY",
    "fish": "FISH_API_KEY",
}

# Deprecated provider removed from the product; kept for migration normalization.
_LIVEKIT_INFERENCE_PROVIDER = "livekit_inference"
_INFERENCE_STAGE_DEFAULTS: dict[str, str] = {
    "stt": "deepgram",
    "llm": "openai",
    "tts": "cartesia",
}


class OrganizationCredentialResolutionError(RuntimeError):
    """Raised when an organization credential blob cannot be authenticated."""


def normalize_stage_provider(provider: str, *, stage: str = "") -> str:
    """Map deprecated ``livekit_inference`` stages to direct provider keys."""
    if provider == _LIVEKIT_INFERENCE_PROVIDER:
        return _INFERENCE_STAGE_DEFAULTS.get(stage, "openai")
    return provider


def _providers_needed(speech_config: SpeechConfig) -> set[str]:
    """Return the set of api_keys entries the config requires.

    Args:
        speech_config: A validated RealtimeSpeechConfig or PipelineSpeechConfig.

    Returns:
        The configured realtime provider or the per-stage direct providers for
        pipeline. Providers without an env mapping (e.g. ``silero``) are
        excluded — they need no key.

    Raises:
        TypeError: If ``speech_config`` is neither realtime nor pipeline config.
    """
    if isinstance(speech_config, RealtimeSpeechConfig):
        return {speech_config.provider}
    if isinstance(speech_config, PipelineSpeechConfig):
        needed: set[str] = set()
        for stage_name, stage in (
            ("stt", speech_config.stt),
            ("llm", speech_config.llm),
            ("tts", speech_config.tts),
        ):
            provider = normalize_stage_provider(stage.provider, stage=stage_name)
            if provider in _PLATFORM_ENV:
                needed.add(provider)
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
        ``{"google": ..., "deepgram": ...}``), or ``{}`` if there is no org or
        no encrypted blob.

    Raises:
        OrganizationCredentialResolutionError: If a non-empty encrypted blob
            cannot be authenticated. Callers must not silently switch to a
            platform credential in that case.
    """
    if org is None:
        return {}
    creds: dict[str, Any] = {}
    blob = getattr(org, "provider_credentials", None)
    if blob:
        try:
            decrypted = decrypt_data(blob)
            if isinstance(decrypted, dict):
                creds = decrypted
        except Exception as e:  # pragma: no cover - defensive, logged
            logger.error(
                "Failed to decrypt provider_credentials for org %s (%s)",
                getattr(org, "id", "<unknown>"),
                type(e).__name__,
            )
            raise OrganizationCredentialResolutionError(
                "organization provider credentials could not be decrypted"
            ) from None
        if not isinstance(decrypted, dict) or not decrypted:
            logger.error(
                "Refusing to use unreadable provider_credentials for org %s",
                getattr(org, "id", "<unknown>"),
            )
            raise OrganizationCredentialResolutionError(
                "organization provider credentials could not be decrypted"
            )
    # Transitional legacy-column fallback. The staged data migration clears
    # this value before the compatibility column is removed.
    if not creds.get("google"):
        legacy_google = getattr(org, "google_api_key", None)
        if legacy_google:
            creds = {**creds, "google": legacy_google}
    return creds


def resolve_org_provider_credential(org: Optional[Any], provider: str) -> Any:
    """Return one decrypted organization provider credential for runtime use.

    Args:
        org: Organization-like object exposing the encrypted
            ``provider_credentials`` blob.
        provider: Stable provider key, such as ``google`` or ``resend``.

    Returns:
        The requested credential value, or ``None`` when the organization has
        not configured it. The value is intended for a narrowly scoped server
        runtime path and must never be serialized into prompts or API models.
    """
    try:
        return _org_credentials(org).get(provider)
    except OrganizationCredentialResolutionError:
        # Fail closed for the narrowly scoped native-tool path. Returning no
        # credential lets the tool emit its normal safe configuration error;
        # it must never use a stale per-agent or platform fallback.
        return None


def resolve_api_keys(
    speech_config: SpeechConfig,
    org: Optional[Any] = None,
    use_platform_credits: bool = False,
    *,
    allow_platform_fallback: bool = True,
) -> dict[str, Any]:
    """Build the per-provider ``api_keys`` map for a speech config + org.

    See the module docstring for the full resolution priority. Only the providers
    the config actually needs appear in the result.

    Args:
        speech_config: The validated SpeechConfig (realtime or pipeline) loaded
            from the agent's preset, or the System Default preset row for legacy
            agents (``preset_id`` NULL).
        org: The organization the agent belongs to (must expose
            ``provider_credentials``), or ``None``.
        use_platform_credits: When True, always use platform env vars and ignore
            the org's own credentials (mirrors the existing per-agent toggle).
        allow_platform_fallback: When False, omit a provider unless the org (or
            ``use_platform_credits`` platform env) supplies it. Used by the
            org-facing preset catalog so admins are prompted to configure their
            own keys even when the platform env has fallbacks for worker calls.

    Returns:
        The ``api_keys`` map. String providers map to their key string.
        Providers with no resolvable key are omitted.
    """
    needed = _providers_needed(speech_config)
    if use_platform_credits:
        creds = {}
    else:
        try:
            creds = _org_credentials(org)
        except OrganizationCredentialResolutionError:
            # A configured-but-unreadable tenant blob is not equivalent to an
            # unconfigured tenant. Do not silently charge the platform account.
            return {}
    api_keys: dict[str, Any] = {}

    for provider in needed:
        value: Optional[str] = None
        if not use_platform_credits:
            value = creds.get(provider)
        if not value and allow_platform_fallback:
            env_name = _PLATFORM_ENV.get(provider)
            if env_name:
                value = os.environ.get(env_name)
        if value:
            api_keys[provider] = value

    return api_keys


def is_preset_ready(
    speech_config: SpeechConfig,
    org: Optional[Any] = None,
    use_platform_credits: bool = False,
    *,
    org_credentials_only: bool = False,
) -> bool:
    """Return whether a preset's required providers are all resolvable for an org.

    Uses the same resolution path as :func:`resolve_api_keys` but returns a
    single boolean suitable for org-facing catalog APIs (no provider names
    exposed). A preset is **ready** when every provider in
    ``_providers_needed(speech_config)`` appears in the resolved ``api_keys`` map
    with a usable value.

    Args:
        speech_config: Validated realtime or pipeline config from a preset row.
        org: Organization object exposing ``provider_credentials``, or ``None``.
        use_platform_credits: When True, org credentials are ignored (platform
            env vars only), mirroring per-agent billing toggle behavior.
        org_credentials_only: When True (org-facing catalog), ignore platform
            env fallbacks unless ``use_platform_credits`` is also True. Ensures
            realtime presets surface "setup required" when the org has not
            configured Google even if ``GEMINI_API_KEY`` exists in the worker
            environment.

    Returns:
        ``True`` if calls using this preset would resolve all required keys;
        ``False`` otherwise.
    """
    needed = _providers_needed(speech_config)
    if not needed:
        return True
    api_keys = resolve_api_keys(
        speech_config,
        org,
        use_platform_credits,
        allow_platform_fallback=(not org_credentials_only or use_platform_credits),
    )
    for provider in needed:
        if provider not in api_keys:
            return False
        if not api_keys.get(provider):
            return False
    return True


__all__ = [
    "resolve_api_keys",
    "is_preset_ready",
    "normalize_stage_provider",
    "resolve_org_provider_credential",
]
