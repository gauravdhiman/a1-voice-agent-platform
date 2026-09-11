"""Observe Pipecat control/metric frames without copying audio or conversation text."""

from collections import deque

from pipecat.frames.frames import (
    BotStartedSpeakingFrame,
    BotStoppedSpeakingFrame,
    InterruptionFrame,
    MetricsFrame,
    UserStartedSpeakingFrame,
    UserStoppedSpeakingFrame,
)
from pipecat.metrics.metrics import (
    LLMUsageMetricsData,
    ProcessingMetricsData,
    TTFBMetricsData,
    TTSUsageMetricsData,
)
from pipecat.observers.base_observer import BaseObserver, FramePushed

from shared.observability.signals import event, record

_CONTROL_EVENTS = {
    UserStartedSpeakingFrame: "turn.user_started",
    UserStoppedSpeakingFrame: "turn.user_stopped",
    BotStartedSpeakingFrame: "turn.agent_started",
    BotStoppedSpeakingFrame: "turn.agent_stopped",
    InterruptionFrame: "turn.interrupted",
}


class VoiceTelemetryObserver(BaseObserver):
    """Collect native timings and usage with a fixed-size frame deduplication window."""

    def __init__(self):
        super().__init__()
        self._seen = set()
        self._recent = deque(maxlen=1024)

    async def on_push_frame(self, data: FramePushed):
        """Ignore media/text; count each control/metric frame once across processors."""
        frame = data.frame
        name = _CONTROL_EVENTS.get(type(frame))
        if not name and not isinstance(frame, MetricsFrame):
            return
        if frame.id in self._seen:
            return
        if len(self._recent) == self._recent.maxlen:
            self._seen.discard(self._recent[0])
        self._recent.append(frame.id)
        self._seen.add(frame.id)
        if name:
            event(name)
            if name == "turn.interrupted":
                record("platform.voice.interruptions")
            return
        for item in frame.data:
            # Classify a bounded stage. Processor/model names remain trace fields.
            processor = item.processor.lower()
            stage = (
                "tts" if "tts" in processor else "stt" if "stt" in processor else "llm"
            )
            if isinstance(item, (TTFBMetricsData, ProcessingMetricsData)):
                metric = (
                    "platform.ai.ttfb"
                    if isinstance(item, TTFBMetricsData)
                    else "platform.ai.processing"
                )
                if item.value >= 0:
                    record(metric, item.value, kind="histogram", stage=stage)
                    event("ai.timing", stage=stage, duration_ms=item.value * 1000)
            elif isinstance(item, LLMUsageMetricsData):
                for token_type, value in (
                    ("input", item.value.prompt_tokens),
                    ("output", item.value.completion_tokens),
                ):
                    if value >= 0:
                        record(
                            "platform.ai.tokens", value, **{"token.type": token_type}
                        )
                        event("ai.usage", tokens=value, **{"token.type": token_type})
            elif isinstance(item, TTSUsageMetricsData) and item.value >= 0:
                record("platform.ai.tts.characters", item.value)
