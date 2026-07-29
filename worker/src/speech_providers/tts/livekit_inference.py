"""LiveKit Inference TTS pipeline provider.

Builds the kwargs for ``livekit.agents.inference.TTS`` from a
:class:`TTSStageConfig`, then injects the LiveKit credentials and constructs
the plugin. Mirrors the other Inference providers.

``inference.TTS`` takes ``voice`` / ``language`` as top-level kwargs, but
provider-specific options (Cartesia ``speed`` / ``emotion``, ...) route into
``extra_kwargs``.

See :mod:`speech_providers.stt.inference` for the credential-resolution
rationale (single LiveKit Cloud auth; Phase 2b reads the platform key from the
environment; the ``api_key``/``api_secret`` kwargs are the Phase 3 per-org seam).
Constructor kwargs are locked from post-install introspection of
``inference.TTS``.
"""

import os
from typing import Any, Optional

from livekit.agents import inference

from shared.voice_agents.speech_config import TTSStageConfig

# Top-level constructor kwargs on inference.TTS (locked from introspection).
# Provider-specific options (speed, emotion, ...) route into extra_kwargs.
_TOP_LEVEL_TTS_KWARGS = frozenset(
    {"voice", "language", "base_url", "encoding", "sample_rate"}
)


def build_livekit_inference_tts_config(
    config: Optional[TTSStageConfig] = None,
) -> dict[str, Any]:
    """Build the kwargs for ``inference.TTS`` from a stage config.

    Args:
        config: The TTS stage config. If ``None``, a minimal default stage
            config is used.

    Returns:
        dict: kwargs accepted by ``inference.TTS``. Credentials are deliberately
        NOT included (supplied by :func:`build_livekit_inference_tts`). ``model`` is
        always included (Inference has no implicit default — a missing model
        raises ``ValueError``). Known top-level params (``voice`` /
        ``language`` / ...) are forwarded directly; provider-specific params
        route into ``extra_kwargs``.

    Raises:
        ValueError: If ``config.model`` is ``None`` (Inference requires an
            explicit model string like ``"cartesia/sonic-3"``).

    Notes:
        - ``provider`` (the dispatch key) is never forwarded — it is not a
          plugin kwarg.
        - ``params`` must not contain ``api_key`` / ``api_secret``.
    """
    cfg = config if config is not None else TTSStageConfig(provider="livekit_inference")
    if cfg.model is None:
        raise ValueError(
            "LiveKit Inference TTS requires an explicit model string "
            "(e.g. 'cartesia/sonic-3'); config.model is None."
        )
    kwargs: dict[str, Any] = {"model": cfg.model}
    extra: dict[str, Any] = {}
    for key, value in cfg.params.items():
        if key in _TOP_LEVEL_TTS_KWARGS:
            kwargs[key] = value
        else:
            extra[key] = value
    if extra:
        kwargs["extra_kwargs"] = extra
    return kwargs


def build_livekit_inference_tts(
    config: Optional[TTSStageConfig] = None,
    *,
    api_key: Optional[str] = None,
    api_secret: Optional[str] = None,
) -> inference.TTS:
    """Construct the LiveKit Inference TTS plugin with the configured kwargs.

    The plugin is constructed (opts stored) but no network connection is opened
    — the inference call happens on the first turn. Safe to call in tests with
    fake credentials.

    Args:
        config: The TTS stage config (model required). If ``None``, a minimal
            default is used.
        api_key: LiveKit API key. Falls back to ``LIVEKIT_API_KEY`` from the
            environment. Phase 3's per-org key_resolver will pass the tenant's
            key here.
        api_secret: LiveKit API secret. Falls back to ``LIVEKIT_API_SECRET``
            from the environment.

    Returns:
        inference.TTS: the configured (but not yet connected) TTS plugin.

    Raises:
        ValueError: If no LiveKit API key is available.
    """
    resolved_key = api_key or os.environ.get("LIVEKIT_API_KEY")
    resolved_secret = api_secret or os.environ.get("LIVEKIT_API_SECRET")
    if not resolved_key:
        raise ValueError(
            "LiveKit Inference TTS requires a LiveKit API key; pass api_key= "
            "or set LIVEKIT_API_KEY in the environment."
        )
    kwargs = build_livekit_inference_tts_config(config)
    kwargs["api_key"] = resolved_key
    if resolved_secret is not None:
        kwargs["api_secret"] = resolved_secret
    return inference.TTS(**kwargs)


__all__ = ["build_livekit_inference_tts_config", "build_livekit_inference_tts"]
