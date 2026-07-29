"""Silero VAD pipeline provider.

Builds the kwargs for ``livekit.plugins.silero.VAD.load`` from a
:class:`VADConfig`, then loads the VAD. Unlike the cloud stage builders, Silero
is **local/on-device**: it needs no API key and ships a single bundled ONNX
model (``resources/silero_vad.onnx``). The builder calls the sync
``silero.VAD.load(**kwargs)`` classmethod, which loads the bundled model —
fully offline, no network, so it is deterministic and safe in tests.

This is the same Silero model family the HuggingFace ``speech-to-speech``
reference uses (Silero v5). Crucially, building an explicit standalone
``silero.VAD`` keeps the pipeline **off** the bundled
``livekit.agents.inference`` VAD path — the path that preloads
``livekit.agents.inference._warmup`` and is the source of the missing-Pillow
error (deferred bug #7). See the Phase 2 plan's "VAD default nuance" section.

Only the open ``params`` dict is forwarded to ``VAD.load`` (tuning kwargs like
``min_silence_duration`` / ``activation_threshold``). ``model`` is intentionally
NOT forwarded: ``VAD.load`` takes no ``model`` argument (the ONNX model is
bundled, not selectable). ``api_key`` is never applicable.
"""

from typing import Any, Optional

from livekit.plugins.silero import VAD as SileroVAD

from shared.voice_agents.speech_config import VADConfig


def build_silero_vad_config(
    config: Optional[VADConfig] = None,
) -> dict[str, Any]:
    """Build the kwargs for ``silero.VAD.load`` from a VAD config.

    Args:
        config: The VAD config. If ``None``, an empty kwargs dict is returned
            so all Silero plugin defaults apply.

    Returns:
        dict: kwargs accepted by ``silero.VAD.load``. Only ``config.params`` is
        forwarded. ``model`` is deliberately NOT forwarded — ``VAD.load`` takes
        no ``model`` argument (the ONNX model is bundled). ``api_key`` is never
        included.
    """
    if config is None:
        return {}
    return dict(config.params)


def build_silero_vad(config: Optional[VADConfig] = None) -> SileroVAD:
    """Load the Silero VAD with the configured kwargs.

    Calls the sync ``silero.VAD.load(**kwargs)`` classmethod, which loads the
    bundled ONNX model on CPU (``force_cpu=True`` by default). Fully offline —
    no network, no API key. Safe and deterministic in tests.

    Args:
        config: The VAD config. If ``None``, plugin defaults apply (this is the
            registry's call when ``PipelineSpeechConfig.vad`` is ``None`` — it
            still builds an explicit standalone VAD rather than leaving it to
            the AgentSession default).

    Returns:
        SileroVAD: the loaded, ready-to-use VAD instance.
    """
    return SileroVAD.load(**build_silero_vad_config(config))


__all__ = ["build_silero_vad_config", "build_silero_vad"]
