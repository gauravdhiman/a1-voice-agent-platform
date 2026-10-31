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
each stage may use a different direct provider (deepgram, openai, cartesia,
cerebras, etc.). ``preset_type`` is a denormalized filter column derived
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


class PresetCredentialSource(str, Enum):
    """Credential boundary used by this voice profile at runtime."""

    PLATFORM = "platform"
    ORGANIZATION = "organization"


# Initial display name for the seeded platform default. It can be reused after
# the default is renamed; an upsert cannot overwrite the current default row.
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
        credential_source: ``platform`` uses the platform's provider keys;
            ``organization`` requires the organization's configured keys (unless
            the agent explicitly opts into platform credits).
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
    credential_source: PresetCredentialSource = Field(
        default=PresetCredentialSource.ORGANIZATION,
        description="Use platform provider keys or organization-configured keys.",
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
    credential_source: Optional[PresetCredentialSource] = Field(
        None, description="Credential boundary for this voice profile."
    )

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
        is_default: True for the platform preset used when an agent has no
            explicit ``preset_id``. There is exactly one, and it must be a
            published platform-credential preset. This is response-only.
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
            "True for the platform preset used when an agent has no preset "
            "selected. Response-only; never accepted as input."
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


class PresetCatalogItem(BaseModel):
    """Org-facing voice profile entry (white-label catalog; no engine/config leak).

    Org admins see only the display name, description, and whether the profile
    is ready for their organization. Underlying providers and ``SpeechConfig``
    are intentionally omitted.
    """

    id: UUID = Field(..., description="Preset ID")
    name: str = Field(..., description="Display name of the voice profile")
    description: Optional[str] = Field(
        None, description="Human-readable description for org admins"
    )
    credential_source: PresetCredentialSource = Field(
        ..., description="Whether the profile uses platform or org credentials."
    )
    is_ready: bool = Field(
        ...,
        description=(
            "True when all credentials required by this profile are configured "
            "for the requesting organization, or platform provider keys are "
            "available for a platform-managed profile."
        ),
    )


class PresetCatalogDefault(BaseModel):
    """Display metadata for the preset selected when ``preset_id`` is null."""

    name: str
    description: Optional[str] = None
    credential_source: PresetCredentialSource = PresetCredentialSource.PLATFORM
    is_ready: bool


class PresetCatalogResponse(BaseModel):
    """Org-facing catalog of published voice profiles with readiness metadata."""

    presets: list[PresetCatalogItem] = Field(
        default_factory=list,
        description="Published voice profiles available for agent assignment.",
    )
    default: Optional[PresetCatalogDefault] = Field(
        None,
        description="Current platform default shown for the null preset selection.",
    )
    default_is_ready: bool = Field(..., description="Readiness of the current default.")
    credentials_self_service: bool = Field(
        default=True,
        description=(
            "When True, org admins may configure API credentials themselves "
            "(transitional self-serve mode). When False, only the platform "
            "admin provisions credentials (managed white-label mode)."
        ),
    )


__all__ = [
    "PresetType",
    "PresetCredentialSource",
    "PresetBase",
    "PresetCreate",
    "PresetUpdate",
    "Preset",
    "PresetUsage",
    "PresetUsageAgent",
    "PresetCatalogItem",
    "PresetCatalogDefault",
    "PresetCatalogResponse",
    "RESERVED_DEFAULT_NAME",
]
