"""Pydantic models for platform-admin-managed voice-engine presets.

A **preset** is a named, platform-admin-managed voice-engine configuration. An
agent references one preset by ``preset_id``; the worker loads that preset
**live on every call** (no versioning — admin edits take effect on the next
call). This module mirrors the structure of :mod:`shared.voice_agents.tool_models`
(the MCP server catalog), since presets are the same kind of platform-admin-managed
global catalog.

Two preset types only — ``realtime`` / ``pipeline`` — matching the
``SpeechConfig`` discriminated union (:mod:`shared.voice_agents.speech_config`).
A "mixed" preset is NOT a third type: it is just a ``pipeline`` preset where
some stages use LiveKit Inference (``provider == "livekit_inference"``) and some
use direct providers. ``preset_type`` is a denormalized filter column derived
from ``config.engine_mode`` on every write by the service — never set by hand.

Presets carry **no secrets**: the per-provider API keys live on the
organization (``organizations.provider_credentials``, encrypted), not in the
preset. The worker's key resolver pairs a preset's ``config`` with the org's
credentials to build the ``api_keys`` map the speech-provider factory expects.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from shared.voice_agents.speech_config import SpeechConfig


class PresetType(str, Enum):
    """The engine mode a preset configures (mirrors ``EngineMode``).

    Attributes:
        REALTIME: End-to-end speech model (Google Gemini native-audio).
        PIPELINE: Modular STT -> LLM -> TTS cascade, each stage swappable.
    """

    REALTIME = "realtime"
    PIPELINE = "pipeline"


# Reserved name for the single system-default preset row (see ``Preset.is_default``).
# The upsert path rejects this name so admins cannot clobber the default row by
# authoring a preset with the same name; the default is managed via its own
# config-editor endpoint.
RESERVED_DEFAULT_NAME = "System Default"


class PresetBase(BaseModel):
    """Base model for a voice-engine preset.

    Attributes:
        name: Unique preset name (1-100 chars).
        description: Optional human-readable description.
        config: The validated ``SpeechConfig`` (realtime or pipeline). FastAPI
            validates the discriminated union on input; the service re-validates
            via ``parse_speech_config`` and derives ``preset_type`` from
            ``config.engine_mode``.
        is_published: Draft↔published lifecycle. ``False`` = draft
            (platform-admin-only); ``True`` = published to the global catalog,
            assignable by org admins to their agents.
    """

    name: str = Field(..., min_length=1, max_length=100, description="Preset name")
    description: Optional[str] = Field(None, description="Preset description")
    config: SpeechConfig = Field(
        ...,
        description=(
            "The validated SpeechConfig (realtime or pipeline discriminated "
            "union). See shared/voice_agents/speech_config.py."
        ),
    )
    is_published: bool = Field(
        default=False,
        description=(
            "Publish lifecycle: False = draft (platform-admin-only), True = "
            "published to the global catalog (assignable by org admins)."
        ),
    )

    # ``preset_type`` is NOT an input field — the service derives it from
    # ``config.engine_mode`` on every write. extra="forbid" rejects any attempt
    # to hand-set it (or any other unknown field) on create.
    model_config = ConfigDict(extra="forbid")


class PresetCreate(PresetBase):
    """Model for creating/upserting a preset (by name)."""

    pass


class PresetUpdate(BaseModel):
    """Model for updating a preset (all fields optional).

    When ``config`` is supplied the service re-validates it and re-derives
    ``preset_type`` from its ``engine_mode``.
    """

    name: Optional[str] = Field(
        None, min_length=1, max_length=100, description="Preset name"
    )
    description: Optional[str] = Field(None, description="Preset description")
    config: Optional[SpeechConfig] = Field(
        None,
        description=(
            "The validated SpeechConfig. When set, preset_type is re-derived "
            "from config.engine_mode."
        ),
    )
    is_published: Optional[bool] = Field(None, description="Publish lifecycle toggle.")

    # ``preset_type`` is NOT an input field — the service re-derives it from
    # ``config.engine_mode`` when config changes. extra="forbid" rejects any
    # attempt to hand-set it (or any other unknown field) on update.
    model_config = ConfigDict(extra="forbid")


class Preset(PresetBase):
    """Model for a preset with all attributes (API response + worker read).

    Attributes:
        id: Preset ID.
        preset_type: Denormalized from ``config.engine_mode``; set by the
            service on every write, never accepted as input.
        is_default: True only for the single **system-default** preset row —
            the fallback config an agent uses when it has no preset selected
            (``preset_id`` NULL, e.g. a legacy agent or one whose preset was
            deleted). Seeded by the migration with today's realtime config; the
            platform admin edits its ``config`` via a dedicated endpoint (it is
            NOT publishable/deletable, and never appears in the org-admin picker
            because it is not published). This is a **response-only** field: it
            is not accepted on ``PresetCreate``/``PresetUpdate`` (``extra=
            "forbid"`` rejects a hand-set value); the service sets it only on the
            seeded default row.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
    """

    id: UUID = Field(..., description="Preset ID")
    preset_type: PresetType = Field(
        ..., description="Engine mode (realtime|pipeline); derived from config."
    )
    is_default: bool = Field(
        default=False,
        description=(
            "True only for the single system-default preset row (the fallback "
            "config for an agent with no preset selected). Response-only; never "
            "accepted as input."
        ),
    )
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class PresetUsageAgent(BaseModel):
    """A single agent referencing a preset (for the delete guardrail listing)."""

    id: UUID = Field(..., description="Agent ID")
    name: str = Field(..., description="Agent name")
    organization_id: UUID = Field(..., description="Owning organization ID")


class PresetUsage(BaseModel):
    """Usage summary for a preset (used-by-N-agents guardrail for delete)."""

    count: int = Field(..., description="Number of agents referencing the preset")
    agents: list[PresetUsageAgent] = Field(
        default_factory=list,
        description="Agents referencing the preset (id, name, organization_id).",
    )


__all__ = [
    "PresetType",
    "PresetBase",
    "PresetCreate",
    "PresetUpdate",
    "Preset",
    "PresetUsage",
    "PresetUsageAgent",
    "RESERVED_DEFAULT_NAME",
]
