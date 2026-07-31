"""OpenAI LLM pipeline provider.

Builds the kwargs for ``livekit.plugins.openai.LLM`` from an
:class:`LLMStageConfig`, then injects the API key and constructs the plugin.
Mirrors :mod:`speech_providers.realtime.provider`: a pure
``build_openai_llm_config`` (no api_key) + ``build_openai_llm`` (constructs the
plugin, no network until session start).

OpenAI is the Phase 2 LLM provider (matches the HuggingFace speech-to-speech
default of the OpenAI Responses API). The plugin default (``model="gpt-4.1"``)
applies when the config omits ``model``; per-stage tuning (temperature,
max_completion_tokens, etc.) is forwarded via ``config.params``.

Constructor kwargs are locked from post-install introspection of
``openai.LLM``. Only ``model`` (when set) and the open ``params`` dict are
forwarded; ``api_key`` is injected separately and ``provider`` is never passed.
"""

from typing import Any, Optional

from livekit.plugins.openai import LLM as OpenAILLM

from shared.voice_agents.speech_config import LLMStageConfig


def build_openai_llm_config(
    config: Optional[LLMStageConfig] = None,
) -> dict[str, Any]:
    """Build the kwargs for ``openai.LLM`` from a stage config.

    Args:
        config: The LLM stage config. If ``None``, a minimal default stage
            config is used so all OpenAI plugin defaults apply.

    Returns:
        dict: kwargs accepted by ``openai.LLM``. ``api_key`` is deliberately
        NOT included (supplied by :func:`build_openai_llm`). ``model`` is
        included only when the config sets it — otherwise omitted so the plugin
        default (gpt-4.1) applies. ``config.params`` is forwarded verbatim.
    """
    cfg = config if config is not None else LLMStageConfig(provider="openai")
    kwargs: dict[str, Any] = {}
    if cfg.model is not None:
        kwargs["model"] = cfg.model
    kwargs.update(cfg.params)
    return kwargs


def build_openai_llm(
    api_key: str,
    config: Optional[LLMStageConfig] = None,
) -> OpenAILLM:
    """Construct the OpenAI LLM plugin with the configured kwargs.

    The plugin is constructed (opts stored) but no network connection is opened
    — the API call happens on the first turn. Safe to call in tests with a fake
    key.

    Args:
        api_key: The OpenAI API key (per-org / platform).
        config: The LLM stage config. If ``None``, plugin defaults apply.

    Returns:
        OpenAILLM: the configured (but not yet connected) LLM plugin.
    """
    return OpenAILLM(api_key=api_key, **build_openai_llm_config(config))


__all__ = ["build_openai_llm_config", "build_openai_llm"]
