"""Turn-detection / endpointing pipeline providers.

Package stub for the pipeline engine's turn-detection stage. **No builder is
wired here in Phase 2** — the pipeline runs on LiveKit's default VAD-based turn
detection (``turn_detection`` omitted from ``AgentSession``). An explicit
turn-detector builder (e.g. an RNT / speculative-turn-tracker adapter, modeled
on HuggingFace's ``SpeculativeTurnTracker``) is deferred to Phase 5 latency
hardening. The registry raises ``NotImplementedError`` for any non-``None``
``TurnDetectionConfig`` until then; this package exists so the import path
``speech_providers.turn_detection`` is reserved and discoverable.

TODO: [Phase 5] Add a turn-detector builder (RNT / speculative turn tracking)
here once latency hardening lands. Rationale: the default VAD-based turn
detection adds end-of-turn dead-air; a speculative tracker cuts that latency.
Priority: Medium. Timeline: Phase 5 voice-engine latency hardening.
"""
