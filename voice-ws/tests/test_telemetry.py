"""Pinned Pipecat observer contracts: bounded memory, no media/text capture."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from pipecat.frames.frames import (
    BotStartedSpeakingFrame,
    BotStoppedSpeakingFrame,
    InterruptionFrame,
    MetricsFrame,
    TextFrame,
    UserStartedSpeakingFrame,
    UserStoppedSpeakingFrame,
)
from pipecat.metrics.metrics import (
    LLMTokenUsage,
    LLMUsageMetricsData,
    ProcessingMetricsData,
    TTFBMetricsData,
    TTSUsageMetricsData,
)
from src import telemetry


@pytest.mark.asyncio
async def test_metric_frames_once_no_payload(monkeypatch):
    record = Mock()
    event = Mock()
    monkeypatch.setattr(telemetry, "record", record)
    monkeypatch.setattr(telemetry, "event", event)
    observer = telemetry.VoiceTelemetryObserver()
    await observer.on_push_frame(SimpleNamespace(frame=TextFrame("private transcript")))
    event.assert_not_called()
    frame = MetricsFrame(
        data=[
            TTFBMetricsData(processor="Gemini", value=0.2),
            ProcessingMetricsData(processor="STT", value=0.4),
            TTFBMetricsData(processor="TTS", value=-1),
            LLMUsageMetricsData(
                processor="Gemini",
                value=LLMTokenUsage(
                    prompt_tokens=10, completion_tokens=4, total_tokens=14
                ),
            ),
            TTSUsageMetricsData(processor="TTS", value=25),
        ]
    )
    data = SimpleNamespace(frame=frame)
    await observer.on_push_frame(data)
    count = record.call_count
    await observer.on_push_frame(data)
    assert record.call_count == count == 5
    assert "private" not in str(event.call_args_list)
    assert any(c.args[0] == "platform.ai.tokens" for c in record.call_args_list)


@pytest.mark.asyncio
async def test_control_frames_and_bounded_deduplication(monkeypatch):
    record = Mock()
    event = Mock()
    monkeypatch.setattr(telemetry, "record", record)
    monkeypatch.setattr(telemetry, "event", event)
    observer = telemetry.VoiceTelemetryObserver()
    for cls in [
        UserStartedSpeakingFrame,
        UserStoppedSpeakingFrame,
        BotStartedSpeakingFrame,
        BotStoppedSpeakingFrame,
        InterruptionFrame,
    ]:
        await observer.on_push_frame(SimpleNamespace(frame=cls()))
    assert event.call_count == 5
    record.assert_called_once_with("platform.voice.interruptions")
    for _ in range(1100):
        await observer.on_push_frame(SimpleNamespace(frame=UserStartedSpeakingFrame()))
    assert len(observer._seen) == len(observer._recent) == 1024
