"""LiveKit Inference STT pipeline provider.

Builds the kwargs for ``livekit.agents.inference.STT`` from an
:class:`STTStageConfig`, then injects the LiveKit credentials and constructs the
plugin. Mirrors the other pipeline providers: a pure
``build_livekit_inference_stt_config`` (no credentials — deterministic, unit-testable) +
``build_livekit_inference_stt`` (constructs the plugin, no network until session start).

LiveKit Inference gives access to many STT models (Deepgram, AssemblyAI, ...)
through a **single LiveKit Cloud auth** — one ``api_key`` + ``api_secret`` —
rather than a per-provider key. That is why Inference stages take a special
dispatch path in :mod:`speech_providers.registry` (no per-stage key guard):
the LiveKit key is shared across all Inference stages in a pipeline.

Credential resolution (Phase 2b): the builder reads ``LIVEKIT_API_KEY`` /
``LIVEKIT_API_SECRET`` from the environment (the platform's LiveKit key). The
``api_key`` / ``api_secret`` keyword args are the forward-compatible seam
Phase 3's per-org ``key_resolver`` will inject into — a tenant can bring its
own LiveKit key for Inference without changing this builder.

Unlike the direct providers, Inference has **no implicit default model** — a
model string (e.g. ``"deepgram/nova-3"``) is required, so the config function
raises ``ValueError`` if ``config.model`` is ``None``. Constructor kwargs are
locked from post-install introspection of ``inference.STT``: known top-level
kwargs (``language`` / ``base_url`` / ``encoding`` / ``sample_rate``) are
forwarded directly, and provider-specific options (e.g. Deepgram ``keywords``)
route into ``extra_kwargs`` (they are not top-level on ``inference.STT``).
"""

import os
from typing import Any, Optional

from livekit.agents import inference

from shared.voice_agents.speech_config import STTStageConfig

# Top-level constructor kwargs on inference.STT (locked from introspection).
# Anything in config.params NOT in this set routes into extra_kwargs.
_TOP_LEVEL_STT_KWARGS = frozenset({"language", "base_url", "encoding", "sample_rate"})


def build_livekit_inference_stt_config(
    config: Optional[STTStageConfig] = None,
) -> dict[str, Any]:
    """Build the kwargs for ``inference.STT`` from a stage config.

    Args:
        config: The STT stage config. If ``None``, a minimal default stage
            config is used.

    Returns:
        dict: kwargs accepted by ``inference.STT``. Credentials are deliberately
        NOT included (supplied by :func:`build_livekit_inference_stt`). ``model`` is
        always included (Inference has no implicit default — a missing model
        raises ``ValueError``). Known top-level params are forwarded directly;
        provider-specific params route into ``extra_kwargs``.

    Raises:
        ValueError: If ``config.model`` is ``None`` (Inference requires an
            explicit model string like ``"deepgram/nova-3"``).

    Notes:
        - ``provider`` (the dispatch key) is never forwarded — it is not a
          plugin kwarg.
        - ``params`` must not contain ``api_key`` / ``api_secret``; if it does,
          the explicit credentials from :func:`build_livekit_inference_stt` collide.
          This is a caller contract, not validated here.
    """
    cfg = config if config is not None else STTStageConfig(provider="livekit_inference")
    if cfg.model is None:
        raise ValueError(
            "LiveKit Inference STT requires an explicit model string "
            "(e.g. 'deepgram/nova-3'); config.model is None."
        )
    kwargs: dict[str, Any] = {"model": cfg.model}
    extra: dict[str, Any] = {}
    for key, value in cfg.params.items():
        if key in _TOP_LEVEL_STT_KWARGS:
            kwargs[key] = value
        else:
            extra[key] = value
    if extra:
        kwargs["extra_kwargs"] = extra
    return kwargs


def build_livekit_inference_stt(
    config: Optional[STTStageConfig] = None,
    *,
    api_key: Optional[str] = None,
    api_secret: Optional[str] = None,
) -> inference.STT:
    """Construct the LiveKit Inference STT plugin with the configured kwargs.

    The plugin is constructed (opts stored) but no network connection is opened
    — the inference call happens on the first turn. Safe to call in tests with
    fake credentials.

    Args:
        config: The STT stage config. If ``None``, a minimal default is used
            (but a model is still required — see
            :func:`build_livekit_inference_stt_config`).
        api_key: LiveKit API key. Falls back to ``LIVEKIT_API_KEY`` from the
            environment. Phase 3's per-org key_resolver will pass the tenant's
            key here.
        api_secret: LiveKit API secret. Falls back to ``LIVEKIT_API_SECRET``
            from the environment.

    Returns:
        inference.STT: the configured (but not yet connected) STT plugin.

    Raises:
        ValueError: If no LiveKit API key is available (neither passed nor in
            the environment) — Inference cannot authenticate without one.
    """
    resolved_key = api_key or os.environ.get("LIVEKIT_API_KEY")
    resolved_secret = api_secret or os.environ.get("LIVEKIT_API_SECRET")
    if not resolved_key:
        raise ValueError(
            "LiveKit Inference STT requires a LiveKit API key; pass api_key= "
            "or set LIVEKIT_API_KEY in the environment."
        )
    kwargs = build_livekit_inference_stt_config(config)
    kwargs["api_key"] = resolved_key
    if resolved_secret is not None:
        kwargs["api_secret"] = resolved_secret
    return inference.STT(**kwargs)


__all__ = ["build_livekit_inference_stt_config", "build_livekit_inference_stt"]
