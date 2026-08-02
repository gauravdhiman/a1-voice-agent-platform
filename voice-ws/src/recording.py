"""Recording hooks for future call-recording feature.

Phase 1 does not persist audio. This module defines a no-op tee so the
pipeline can later attach a real buffer/uploader without changing transport
wiring.

TODO: [Feature] Call recording
Rationale: Persist bidirectional PCM/Opus for compliance and playback UI.
Priority: Medium
Timeline: After Phase 2 (phone) when session lifecycle is stable.
Approach: Replace NoOpRecordingTee with Pipecat AudioBufferProcessor (or
custom FrameProcessor) that muxes user+agent audio and uploads to object
storage on session end.
"""

from __future__ import annotations

import logging
from typing import Optional

from pipecat.frames.frames import Frame
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

logger = logging.getLogger(__name__)


class NoOpRecordingTee(FrameProcessor):
    """Pass-through processor reserved for future bidirectional audio capture.

    Inserted in the pipeline so recording can be enabled later by swapping
    this class for a buffering implementation without reshaping the graph.
    """

    def __init__(self, *, session_id: Optional[str] = None, enabled: bool = False):
        """Initialize the tee.

        Args:
            session_id: Voice session id (for future artifact naming).
            enabled: When True, log that recording would capture frames
                (still does not persist in Phase 1).
        """
        super().__init__()
        self._session_id = session_id
        self._enabled = enabled
        self._frame_count = 0

    async def process_frame(self, frame: Frame, direction: FrameDirection) -> None:
        """Forward every frame unchanged; optionally count when enabled."""
        await super().process_frame(frame, direction)
        if self._enabled:
            self._frame_count += 1
            if self._frame_count == 1:
                logger.info(
                    "Recording tee active for session_id=%s (Phase 1: no persistence)",
                    self._session_id,
                )
        await self.push_frame(frame, direction)
