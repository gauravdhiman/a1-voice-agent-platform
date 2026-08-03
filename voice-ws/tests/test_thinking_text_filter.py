"""Tests for stripping Gemma/OpenRouter thinking channel artifacts from TTS text."""

from __future__ import annotations

import pytest

from src.speech.thinking_text_filter import (
    ThinkingChannelTextFilter,
    strip_thinking_artifacts,
)


class TestStripThinkingArtifacts:
    """Unit tests for the pure string sanitizer used before TTS."""

    def test_strips_gemma_channel_thought_block(self) -> None:
        """Exact leak observed in Fish TTS logs must become empty / speakable."""
        leaked = "<|channel>thought\n<channel|>"
        assert strip_thinking_artifacts(leaked) == ""
        # The channel body word must not remain as speakable text either.
        assert "thought" not in strip_thinking_artifacts(leaked).lower()

    def test_preserves_spoken_prefix_before_channel_leak(self) -> None:
        """User-facing words before a thinking leak must remain."""
        text = "Let me check that for you. One moment please. <|channel>thought\n<channel|>"
        assert strip_thinking_artifacts(text) == "Let me check that for you. One moment please."
        assert "thought" not in strip_thinking_artifacts(text).lower()
        assert "channel" not in strip_thinking_artifacts(text).lower()

    def test_leaves_normal_speech_unchanged(self) -> None:
        """Ordinary assistant replies must pass through untouched."""
        text = "Yes, Monday at ten a.m. is available."
        assert strip_thinking_artifacts(text) == text

    def test_strips_think_xml_blocks(self) -> None:
        """Generic think wrappers used by other models are also removed."""
        text = "<think>internal plan</think>I can help with that."
        assert strip_thinking_artifacts(text) == "I can help with that."


class TestThinkingChannelTextFilter:
    """Async Pipecat BaseTextFilter adapter."""

    @pytest.mark.asyncio
    async def test_filter_removes_channel_markers(self) -> None:
        """Filter contract used by TTS text_filters must sanitize chunks."""
        filt = ThinkingChannelTextFilter()
        result = await filt.filter("Checking now. <|channel>thought\n<channel|>")
        assert result == "Checking now."
        assert "channel" not in result.lower()
        assert "thought" not in result.lower()
