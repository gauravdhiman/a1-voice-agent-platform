"""LLM (language model) pipeline providers.

Re-exports the per-provider LLM builders. Phase 2 ships OpenAI (direct);
Phase 2b adds Cerebras (direct, OpenAI-compatible, high throughput).
Additional providers (Anthropic, Google, Groq, a local Ollama adapter via
``openai.LLM.with_ollama``) are added as a new module + a branch in
:mod:`speech_providers.registry`.
"""

from speech_providers.llm.cerebras import build_cerebras_llm, build_cerebras_llm_config
from speech_providers.llm.openai import build_openai_llm, build_openai_llm_config

__all__ = [
    "build_openai_llm_config",
    "build_openai_llm",
    "build_cerebras_llm_config",
    "build_cerebras_llm",
]
