"""Cerebras LLM pipeline provider (direct, OpenAI-compatible).

Builds the kwargs for ``livekit.plugins.openai.LLM.with_cerebras`` from an
:class:`LLMStageConfig`, then injects the API key and constructs the plugin.
Mirrors :mod:`speech_providers.llm.openai`: a pure ``build_cerebras_llm_config``
(no api_key — deterministic, unit-testable) + ``build_cerebras_llm`` (constructs
the plugin, no network until the first turn).

Cerebras is a direct OpenAI-compatible LLM provider chosen for **high
throughput / low latency** — it rides the normal keyed dispatch path (a
``"cerebras"`` entry in :data:`LLM_BUILDERS`), so a pipeline can mix it with
Inference stages (e.g. Inference STT + Cerebras LLM + Inference TTS). It is NOT
a LiveKit Inference stage — it has its own per-org / platform API key, read
from ``api_keys["cerebras"]`` by the registry's keyed path.

Constructor kwargs are locked from post-install introspection of
``openai.LLM.with_cerebras``. Only ``model`` (when set) and the open ``params``
dict are forwarded; ``api_key`` is injected separately. The plugin default
model is ``llama-4-scout-17b-16e-instruct``; ``temperature`` is a top-level
kwarg here (unlike ``inference.LLM``).
"""

from typing import Any, Optional

from livekit.plugins.openai import LLM as OpenAILLM

from shared.voice_agents.speech_config import LLMStageConfig


def build_cerebras_llm_config(
    config: Optional[LLMStageConfig] = None,
) -> dict[str, Any]:
    """Build the kwargs for ``openai.LLM.with_cerebras`` from a stage config.

    Args:
        config: The LLM stage config. If ``None``, a minimal default stage
            config is used so all Cerebras plugin defaults apply.

    Returns:
        dict: kwargs accepted by ``openai.LLM.with_cerebras``. ``api_key`` is
        deliberately NOT included (supplied by :func:`build_cerebras_llm`).
        ``model`` is included only when the config sets it — otherwise omitted
        so the plugin default (llama-4-scout-17b-16e-instruct) applies.
        ``config.params`` is forwarded verbatim.

    Notes:
        - ``provider`` (the dispatch key) is never forwarded — it is not a
          plugin kwarg.
        - ``params`` must not contain ``api_key``; if it does, the explicit
          ``api_key`` from :func:`build_cerebras_llm` would collide. This is a
          caller contract, not validated here.
    """
    cfg = config if config is not None else LLMStageConfig(provider="cerebras")
    kwargs: dict[str, Any] = {}
    if cfg.model is not None:
        kwargs["model"] = cfg.model
    kwargs.update(cfg.params)
    return kwargs


def build_cerebras_llm(
    api_key: str,
    config: Optional[LLMStageConfig] = None,
) -> OpenAILLM:
    """Construct the Cerebras LLM plugin with the configured kwargs.

    The plugin is constructed (opts stored) but no network connection is opened
    — the API call happens on the first turn. Safe to call in tests with a fake
    key.

    Args:
        api_key: The Cerebras API key (per-org / platform).
        config: The LLM stage config. If ``None``, plugin defaults apply.

    Returns:
        OpenAILLM: the configured (but not yet connected) LLM plugin (an
        ``openai.LLM`` pointed at the Cerebras base_url).
    """
    return OpenAILLM.with_cerebras(api_key=api_key, **build_cerebras_llm_config(config))


__all__ = ["build_cerebras_llm_config", "build_cerebras_llm"]
