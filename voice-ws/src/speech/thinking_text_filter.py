"""Strip model thinking/channel artifacts so they are never spoken by TTS.

Gemma-family models (including ``google/gemma-4-*`` via OpenRouter) sometimes
emit internal channel markers into assistant ``content``, e.g.::

    <|channel>thought
    <channel|>

Pipecat forwards that text to TTS, so the caller hears phrases like
"channel thought" / "thinking mode". This filter removes those control tokens
(and similar ``<think>`` wrappers) before synthesis.
"""

from __future__ import annotations

import re
from typing import Any, Mapping

from pipecat.utils.text.base_text_filter import BaseTextFilter

# Gemma channel markers (exact leak seen in voice-ws Fish TTS logs) plus common
# think-tag wrappers used by other reasoning models.
# Opening forms seen in the wild:
#   <|channel>thought ... <channel|>
#   <|channel|>thought ... <|channel|>
_CHANNEL_BLOCK_RE = re.compile(
    r"<\|channel\|?>[\s\S]*?(?:<channel\|>|<\|channel\|>)",
    re.IGNORECASE,
)
_CHANNEL_TOKEN_RE = re.compile(
    r"<\|/?channel\|?>|<channel\|>",
    re.IGNORECASE,
)
_THINK_BLOCK_RE = re.compile(
    r"<think\b[^>]*>[\s\S]*?</think>",
    re.IGNORECASE,
)
_THINK_TOKEN_RE = re.compile(r"</?think\b[^>]*>", re.IGNORECASE)
_WHITESPACE_RE = re.compile(r"[ \t]{2,}")


def strip_thinking_artifacts(text: str) -> str:
    """Remove thinking/channel control tokens from model text.

    Args:
        text: Raw assistant text that may contain Gemma channel markers or
            ``<think>`` blocks.

    Returns:
        Speakable text with control tokens removed and excess whitespace
        collapsed. May be empty when the entire chunk was thinking noise.
    """
    if not text:
        return text
    cleaned = _CHANNEL_BLOCK_RE.sub(" ", text)
    cleaned = _CHANNEL_TOKEN_RE.sub(" ", cleaned)
    cleaned = _THINK_BLOCK_RE.sub(" ", cleaned)
    cleaned = _THINK_TOKEN_RE.sub(" ", cleaned)
    cleaned = _WHITESPACE_RE.sub(" ", cleaned)
    # Preserve intentional newlines but drop leftover blank padding.
    cleaned = "\n".join(line.rstrip() for line in cleaned.splitlines())
    return cleaned.strip()


class ThinkingChannelTextFilter(BaseTextFilter):
    """Pipecat TTS text filter that drops leaked model thinking tokens.

    Attach via ``text_filters=[ThinkingChannelTextFilter()]`` on Cartesia/Fish
    (or any) TTS service so pipeline speech never vocalizes control markers.
    """

    async def update_settings(self, settings: Mapping[str, Any]) -> None:
        """No runtime settings — present for the BaseTextFilter contract."""

    async def filter(self, text: str) -> str:
        """Return text with thinking/channel artifacts removed."""
        return strip_thinking_artifacts(text)

    async def handle_interruption(self) -> None:
        """Stateless filter — nothing to reset on interruption."""

    async def reset_interruption(self) -> None:
        """Stateless filter — nothing to restore after interruption."""
