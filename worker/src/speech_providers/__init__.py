"""Speech provider package — provider builders for the voice engines.

This package contains the builders that turn a
:class:`shared.voice_agents.speech_config.SpeechConfig` into the concrete
LiveKit plugin instance(s) the session needs. It is the modular, swappable
core of the voice engine: adding a provider = one new builder module + one
branch in the relevant factory.

Layout:

- ``realtime/`` — the end-to-end realtime engine (Google Gemini native-audio).
  ``realtime.provider.build_realtime_model`` constructs the single
  ``RealtimeModel`` passed as ``llm=`` to ``AgentSession``.
- ``registry.py`` — the factory that dispatches a ``SpeechConfig`` to the right
  engine's components (``RealtimeComponents`` / ``PipelineComponents``).

Phase 2 adds ``stt/``, ``llm/``, ``tts/``, ``vad/``, ``turn_detection/``
factories for the pipeline engine, modeled on HuggingFace's
``speech-to-speech`` ``get_stt_handler`` / ``get_llm_handler`` /
``get_tts_handler`` factory pattern — but each builder returns a LiveKit
plugin instance (not a custom handler), so the session stays on LiveKit's
asyncio runtime.
"""
