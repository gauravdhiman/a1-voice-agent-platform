"""Deepgram STT pipeline provider.

Builds the kwargs for ``livekit.plugins.deepgram.STT`` from an
:class:`STTStageConfig`, then injects the API key and constructs the plugin.
This mirrors :mod:`speech_providers.realtime.provider`: a pure
``build_deepgram_stt_config`` (no api_key — deterministic, unit-testable) +
``build_deepgram_stt`` (constructs the plugin, no network until session start).

Deepgram is the Phase 2 STT provider: streaming nova-3 with server-side
endpointing. The plugin defaults (``model="nova-3"``, ``language="en-US"``)
apply when the config omits them; per-stage tuning (language, smart_format,
keyterms, endpointing) is forwarded via ``config.params``.

Constructor kwargs are locked from post-install introspection of
``deepgram.STT`` — see the Phase 2 plan. Only ``model`` (when set) and the
open ``params`` dict are forwarded; ``api_key`` is injected separately and
``provider`` (the dispatch key) is never passed to the plugin.
"""

from typing import Any, Optional

from livekit.plugins.deepgram import STT as DeepgramSTT

from shared.voice_agents.speech_config import STTStageConfig


def build_deepgram_stt_config(
    config: Optional[STTStageConfig] = None,
) -> dict[str, Any]:
    """Build the kwargs for ``deepgram.STT`` from a stage config.

    Args:
        config: The STT stage config. If ``None``, a minimal default stage
            config is used so all Deepgram plugin defaults apply.

    Returns:
        dict: kwargs accepted by ``deepgram.STT``. ``api_key`` is deliberately
        NOT included (it is agent-specific; supplied by
        :func:`build_deepgram_stt`). ``model`` is included only when the config
        sets it — otherwise it is omitted so the plugin default (nova-3)
        applies. ``config.params`` is forwarded verbatim as extra kwargs.

    Notes:
        - ``provider`` (the dispatch key) is never forwarded — it is not a
          plugin kwarg.
        - ``params`` must not contain ``api_key``; if it does, the explicit
          ``api_key`` from :func:`build_deepgram_stt` would collide. This is a
          caller contract, not validated here.
    """
    cfg = config if config is not None else STTStageConfig(provider="deepgram")
    kwargs: dict[str, Any] = {}
    if cfg.model is not None:
        kwargs["model"] = cfg.model
    kwargs.update(cfg.params)
    return kwargs


def build_deepgram_stt(
    api_key: str,
    config: Optional[STTStageConfig] = None,
) -> DeepgramSTT:
    """Construct the Deepgram STT plugin with the configured kwargs.

    The plugin is constructed (opts stored) but no network connection is opened
    — the WebSocket opens on session start. Safe to call in tests with a fake
    key.

    Args:
        api_key: The Deepgram API key (per-org / platform).
        config: The STT stage config. If ``None``, plugin defaults apply.

    Returns:
        DeepgramSTT: the configured (but not yet connected) STT plugin.
    """
    return DeepgramSTT(api_key=api_key, **build_deepgram_stt_config(config))


__all__ = ["build_deepgram_stt_config", "build_deepgram_stt"]
