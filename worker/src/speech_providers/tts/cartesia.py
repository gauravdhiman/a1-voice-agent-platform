"""Cartesia TTS pipeline provider.

Builds the kwargs for ``livekit.plugins.cartesia.TTS`` from a
:class:`TTSStageConfig`, then injects the API key and constructs the plugin.
Mirrors :mod:`speech_providers.realtime.provider`: a pure
``build_cartesia_tts_config`` (no api_key) + ``build_cartesia_tts`` (constructs
the plugin, no network until session start).

Cartesia is the Phase 2 TTS provider (sub-200ms TTFB). The plugin defaults
(``model="sonic-3"``, a default voice UUID, ``language="en"``) apply when the
config omits them; per-stage tuning (voice, language, speed, emotion) is
forwarded via ``config.params``. Unlike Deepgram/OpenAI, Cartesia stores the
``api_key`` on its ``_opts`` — the builder still injects it via the
``api_key=`` constructor kwarg, not via the config dict.

Constructor kwargs are locked from post-install introspection of
``cartesia.TTS``. Only ``model`` (when set) and the open ``params`` dict are
forwarded; ``api_key`` is injected separately and ``provider`` is never passed.
"""

from typing import Any, Optional

from livekit.plugins.cartesia import TTS as CartesiaTTS

from shared.voice_agents.speech_config import TTSStageConfig


def build_cartesia_tts_config(
    config: Optional[TTSStageConfig] = None,
) -> dict[str, Any]:
    """Build the kwargs for ``cartesia.TTS`` from a stage config.

    Args:
        config: The TTS stage config. If ``None``, a minimal default stage
            config is used so all Cartesia plugin defaults apply.

    Returns:
        dict: kwargs accepted by ``cartesia.TTS``. ``api_key`` is deliberately
        NOT included (supplied by :func:`build_cartesia_tts`). ``model`` is
        included only when the config sets it — otherwise omitted so the plugin
        default (sonic-3) applies. ``config.params`` is forwarded verbatim.
    """
    cfg = config if config is not None else TTSStageConfig(provider="cartesia")
    kwargs: dict[str, Any] = {}
    if cfg.model is not None:
        kwargs["model"] = cfg.model
    kwargs.update(cfg.params)
    return kwargs


def build_cartesia_tts(
    api_key: str,
    config: Optional[TTSStageConfig] = None,
) -> CartesiaTTS:
    """Construct the Cartesia TTS plugin with the configured kwargs.

    The plugin is constructed (opts stored) but no network connection is opened
    — the WebSocket opens on session start. Safe to call in tests with a fake
    key.

    Args:
        api_key: The Cartesia API key (per-org / platform).
        config: The TTS stage config. If ``None``, plugin defaults apply.

    Returns:
        CartesiaTTS: the configured (but not yet connected) TTS plugin.
    """
    return CartesiaTTS(api_key=api_key, **build_cartesia_tts_config(config))


__all__ = ["build_cartesia_tts_config", "build_cartesia_tts"]
