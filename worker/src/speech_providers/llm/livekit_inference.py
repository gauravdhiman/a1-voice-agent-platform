"""LiveKit Inference LLM pipeline provider.

Builds the kwargs for ``livekit.agents.inference.LLM`` from an
:class:`LLMStageConfig`, then injects the LiveKit credentials and constructs
the plugin. Mirrors the other Inference providers.

Key difference from the direct LLM providers: ``inference.LLM`` takes
chat-completion options (``temperature``, ``max_tokens``, ...) in
``extra_kwargs``, NOT as top-level constructor kwargs. The config function
routes the known top-level kwargs (``provider`` / ``base_url`` /
``inference_class``) directly and packs the rest into ``extra_kwargs``, so a
common ``temperature`` param does not ``TypeError``.

See :mod:`speech_providers.stt.inference` for the credential-resolution
rationale (single LiveKit Cloud auth; Phase 2b reads the platform key from the
environment; the ``api_key``/``api_secret`` kwargs are the Phase 3 per-org seam).
Constructor kwargs are locked from post-install introspection of
``inference.LLM``.
"""

import os
from typing import Any, Optional

from livekit.agents import inference

from shared.voice_agents.speech_config import LLMStageConfig

# Top-level constructor kwargs on inference.LLM (locked from introspection).
# Chat-completion options (temperature, max_tokens, ...) route into extra_kwargs.
_TOP_LEVEL_LLM_KWARGS = frozenset({"provider", "base_url", "inference_class"})


def build_livekit_inference_llm_config(
    config: Optional[LLMStageConfig] = None,
) -> dict[str, Any]:
    """Build the kwargs for ``inference.LLM`` from a stage config.

    Args:
        config: The LLM stage config. If ``None``, a minimal default stage
            config is used.

    Returns:
        dict: kwargs accepted by ``inference.LLM``. Credentials are deliberately
        NOT included (supplied by :func:`build_livekit_inference_llm`). ``model`` is
        always included (Inference has no implicit default — a missing model
        raises ``ValueError``). ``provider`` / ``base_url`` /
        ``inference_class`` are forwarded as top-level kwargs; the remaining
        params (e.g. ``temperature``) route into ``extra_kwargs``.

    Raises:
        ValueError: If ``config.model`` is ``None`` (Inference requires an
            explicit model string like ``"google/gemma-4-31b-it"``).

    Notes:
        - ``provider`` is BOTH a StageConfig dispatch key AND a valid top-level
          ``inference.LLM`` kwarg (the upstream inference provider, e.g.
          ``"cerebras"``). If a caller wants to set the inference provider, it
          goes in ``config.params["provider"]``, which is forwarded here.
        - ``params`` must not contain ``api_key`` / ``api_secret``.
    """
    cfg = config if config is not None else LLMStageConfig(provider="livekit_inference")
    if cfg.model is None:
        raise ValueError(
            "LiveKit Inference LLM requires an explicit model string "
            "(e.g. 'google/gemma-4-31b-it'); config.model is None."
        )
    kwargs: dict[str, Any] = {"model": cfg.model}
    extra: dict[str, Any] = {}
    for key, value in cfg.params.items():
        if key in _TOP_LEVEL_LLM_KWARGS:
            kwargs[key] = value
        else:
            extra[key] = value
    if extra:
        kwargs["extra_kwargs"] = extra
    return kwargs


def build_livekit_inference_llm(
    config: Optional[LLMStageConfig] = None,
    *,
    api_key: Optional[str] = None,
    api_secret: Optional[str] = None,
) -> inference.LLM:
    """Construct the LiveKit Inference LLM plugin with the configured kwargs.

    The plugin is constructed (opts stored) but no network connection is opened
    — the inference call happens on the first turn. Safe to call in tests with
    fake credentials.

    Args:
        config: The LLM stage config (model required). If ``None``, a minimal
            default is used.
        api_key: LiveKit API key. Falls back to ``LIVEKIT_API_KEY`` from the
            environment. Phase 3's per-org key_resolver will pass the tenant's
            key here.
        api_secret: LiveKit API secret. Falls back to ``LIVEKIT_API_SECRET``
            from the environment.

    Returns:
        inference.LLM: the configured (but not yet connected) LLM plugin.

    Raises:
        ValueError: If no LiveKit API key is available.
    """
    resolved_key = api_key or os.environ.get("LIVEKIT_API_KEY")
    resolved_secret = api_secret or os.environ.get("LIVEKIT_API_SECRET")
    if not resolved_key:
        raise ValueError(
            "LiveKit Inference LLM requires a LiveKit API key; pass api_key= "
            "or set LIVEKIT_API_KEY in the environment."
        )
    kwargs = build_livekit_inference_llm_config(config)
    kwargs["api_key"] = resolved_key
    if resolved_secret is not None:
        kwargs["api_secret"] = resolved_secret
    return inference.LLM(**kwargs)


__all__ = ["build_livekit_inference_llm_config", "build_livekit_inference_llm"]
