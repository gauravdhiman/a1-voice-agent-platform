"""
Pydantic models for Voice Agent functionality.
"""

import re
from datetime import datetime
from typing import Optional
from urllib.parse import urlsplit
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


def normalize_phone_number(value: Optional[str]) -> Optional[str]:
    """Normalize whitespace and validate an optional E.164 phone number.

    Args:
        value: Phone number entered by a user or received from an API client.

    Returns:
        Canonical E.164 value with all whitespace removed, or ``None`` for an
        empty optional phone number.

    Raises:
        ValueError: If the normalized value is not a valid E.164 number.
    """
    if value is None or value == "":
        return None

    value = re.sub(r"\s+", "", value)
    if value == "":
        return None

    if not re.match(r"^\+[1-9]\d{7,14}$", value):
        raise ValueError(
            "Phone number must be in E.164 format "
            "with at least 8 digits "
            "(e.g., +14155551234 or +441632960000)"
        )
    return value


def normalize_demo_public_result_url(value: Optional[str]) -> Optional[str]:
    """Normalize an optional public demo result URL.

    Args:
        value: URL configured by a platform administrator for a demo receipt.

    Returns:
        A trimmed HTTPS URL, or ``None`` when the setting is blank.

    Raises:
        ValueError: If the value is not an HTTPS URL with a hostname.
    """
    if value is None or value == "":
        return None

    normalized = str(value).strip()
    if not normalized:
        return None
    try:
        parsed = urlsplit(normalized)
        hostname = parsed.hostname
    except ValueError as exc:
        raise ValueError("Demo public result URL must be a valid HTTPS URL") from exc

    if (
        parsed.scheme.lower() != "https"
        or not hostname
        or parsed.username
        or parsed.password
    ):
        raise ValueError("Demo public result URL must be a valid HTTPS URL")
    return normalized


class VoiceAgentBase(BaseModel):
    """Base model for Voice Agent."""

    name: str = Field(..., min_length=1, max_length=100, description="Agent name")
    phone_number: Optional[str] = Field(
        None, max_length=20, description="Twilio phone number"
    )
    is_active: bool = Field(default=True, description="Whether the agent is active")
    persona: Optional[str] = Field(None, description="Agent persona or role")
    tone: Optional[str] = Field(
        None, description="Communication tone (e.g., professional, friendly)"
    )
    mission: Optional[str] = Field(
        None, description="Specific goals or mission for this agent"
    )
    use_platform_credits: bool = Field(
        default=False,
        description="""
        Use platform credits instead of organization API key.
        
        When False (default): Use organization's Google API key if configured,
        otherwise fall back to platform key.
        
        When True: Always use platform API key, even if organization has their
        own API key configured.
        
        This allows organizations to override the use of their own API key
        on a per-agent basis.
        """,
    )
    custom_instructions: Optional[str] = Field(
        None,
        description="""
        Additional context and instructions specific to this agent's role.
        
        Include information such as:
        - Company policies and procedures relevant to this agent type
        - Unique selling points and differentiators (for sales agents)
        - Common customer questions and how to handle them
        - Emergency or after-hours protocols
        - Specific workflows or escalation procedures
        - Any other context that helps this agent handle calls effectively
        
        This information is used to construct the agent's system prompt
        and will be referenced when interacting with callers.
        """,
    )

    instructions_markdown: Optional[str] = Field(
        None,
        description="""
        Full agent instructions in markdown format.

        When provided, this markdown is used as the primary system prompt
        instead of building it from individual fields (persona, tone, mission, etc.).

        Supports template variables for dynamic context injection:
        - {{org.name}} — Organization name
        - {{org.industry}} — Organization industry
        - {{org.location}} — Organization location
        - {{org.business_details}} — Business description
        - {{agent.name}} — Agent name

        System guardrails and tool guidelines are always appended
        regardless of whether markdown instructions are used.
        """,
    )
    preset_id: Optional[UUID] = Field(
        None,
        description=(
            "FK to pipeline_presets.id. The worker loads this preset live each "
            "call to pick the voice engine (realtime or pipeline) + per-stage "
            "models. NULL = legacy agent (or one whose preset was deleted via the "
            "FK ON DELETE SET NULL) -> the System Default preset row "
            "(pipeline_presets.is_default=true); the hardcoded realtime default is "
            "only the ultimate safety net. Assignment "
            "is validated (preset must exist and be published) by the agent "
            "CRUD routes."
        ),
    )
    is_published_on_public_page: bool = Field(
        default=False,
        description=(
            "When true, the agent is listed on the organization's public page "
            "and accepts visitor voice calls."
        ),
    )
    call_recording_enabled: bool = Field(
        default=False,
        description=(
            "When true, calls handled by this agent may be recorded when the "
            "runtime recording feature is enabled."
        ),
    )
    is_demo: bool = Field(
        default=False,
        description=(
            "When true, this agent is a demo agent that bypasses credit and "
            "concurrency checks, is subject to its demo call limits, and is "
            "available on a dedicated public page at /demo/{demo_slug}. "
            "Platform-admin only; defaults to false."
        ),
    )
    demo_slug: Optional[str] = Field(
        None,
        max_length=100,
        description=(
            "Unique slug for the demo public page (e.g. acme-dental-demo). "
            "Required when is_demo is true; must be lowercase alphanumeric "
            "plus hyphens and unique across all demo agents."
        ),
    )
    public_description: Optional[str] = Field(
        None,
        max_length=1000,
        description=(
            "Customer-facing description shown on the public demo page "
            "(/demo/{demo_slug}). Distinct from LLM prompt fields "
            "(persona/mission/custom_instructions) — this is marketing copy "
            "explaining what the agent does and its scope. Shown only when "
            "the agent is public; fallback on the demo page is mission → persona."
        ),
    )
    demo_public_result_url: Optional[str] = Field(
        None,
        max_length=2048,
        description=(
            "Optional HTTPS URL shown on a successful demo receipt as the "
            "public result destination. Platform-admin only; use a dedicated "
            "public demo view or data store."
        ),
    )
    demo_calls_remaining: int = Field(
        default=-1,
        ge=-1,
        description=(
            "Number of demo call reservations remaining. Zero disables new "
            "calls; -1 means unlimited. Applied only when is_demo is true."
        ),
    )
    demo_max_call_duration_seconds: int = Field(
        default=-1,
        ge=-1,
        description=(
            "Maximum duration for each demo call in seconds. A positive value "
            "caps the call; -1 means unlimited. Applied only when is_demo is true."
        ),
    )

    @field_validator("phone_number", mode="before")
    @classmethod
    def validate_phone_number(cls, v: Optional[str]) -> Optional[str]:
        """Normalize spacing and validate the canonical E.164 format."""
        return normalize_phone_number(v)

    @field_validator("demo_slug", mode="before")
    @classmethod
    def validate_demo_slug(cls, v: Optional[str]) -> Optional[str]:
        """Normalize and validate demo slug when supplied."""
        if v is None or v == "":
            return None
        v = str(v).strip().lower()
        v = re.sub(r"\s+", "-", v)
        if not re.match(r"^[a-z0-9-]+$", v):
            raise ValueError(
                "Demo slug can only contain lowercase letters, numbers, and hyphens"
            )
        if len(v) < 2 or len(v) > 100:
            raise ValueError("Demo slug must be between 2 and 100 characters")
        return v

    @field_validator("public_description", mode="before")
    @classmethod
    def validate_public_description(cls, v: Optional[str]) -> Optional[str]:
        """Trim and validate public description."""
        if v is None or v == "":
            return None
        v = str(v).strip()
        if len(v) > 1000:
            raise ValueError("Public description must be at most 1000 characters")
        return v

    @field_validator("demo_public_result_url", mode="before")
    @classmethod
    def validate_demo_public_result_url(cls, v: Optional[str]) -> Optional[str]:
        """Trim and validate the optional demo receipt destination."""
        return normalize_demo_public_result_url(v)

    @field_validator("demo_max_call_duration_seconds")
    @classmethod
    def validate_demo_max_call_duration(cls, v: int) -> int:
        """Allow ``-1`` for unlimited or require a positive duration."""
        if v != -1 and v <= 0:
            raise ValueError(
                "Demo max call duration must be -1 (unlimited) or greater than 0"
            )
        return v


class VoiceAgentCreate(VoiceAgentBase):
    """Model for creating a new voice agent."""

    organization_id: UUID = Field(
        ..., description="Organization ID that agent belongs to"
    )


class VoiceAgentUpdate(BaseModel):
    """Model for updating a voice agent."""

    name: Optional[str] = Field(
        None, min_length=1, max_length=100, description="Agent name"
    )
    phone_number: Optional[str] = Field(
        None, max_length=20, description="Twilio phone number"
    )

    @field_validator("phone_number", mode="before")
    @classmethod
    def normalize_update_phone_number(cls, v: Optional[str]) -> Optional[str]:
        """Normalize and validate phone numbers when an agent is edited."""
        return normalize_phone_number(v)

    is_active: Optional[bool] = Field(None, description="Whether the agent is active")
    persona: Optional[str] = Field(None, description="Agent persona or role")
    tone: Optional[str] = Field(
        None, description="Communication tone (e.g., professional, friendly)"
    )
    mission: Optional[str] = Field(
        None, description="Specific goals or mission for this agent"
    )
    use_platform_credits: Optional[bool] = Field(
        None,
        description="""
        Use platform credits instead of organization API key.
        
        When False: Use organization's Google API key if configured.
        When True: Always use platform API key.
        """,
    )
    custom_instructions: Optional[str] = Field(
        None,
        description="""
        Additional context and instructions specific to this agent's role.
        
        Include information such as:
        - Company policies and procedures relevant to this agent type
        - Unique selling points and differentiators (for sales agents)
        - Common customer questions and how to handle them
        - Emergency or after-hours protocols
        - Specific workflows or escalation procedures
        - Any other context that helps this agent handle calls effectively
        
        This information is used to construct the agent's system prompt
        and will be referenced when interacting with callers.
        """,
    )
    instructions_markdown: Optional[str] = Field(
        None,
        description="Full agent instructions in markdown format.",
    )
    preset_id: Optional[UUID] = Field(
        None,
        description=(
            "FK to pipeline_presets.id. If set, the preset must exist and be "
            "published (validated by the route). NULL clears the preset (agent "
            "falls back to the System Default preset row)."
        ),
    )
    is_published_on_public_page: Optional[bool] = Field(
        None,
        description=(
            "When true, the agent appears on the organization's public page "
            "(/o/{slug}) and can receive visitor voice calls. Requires the "
            "agent to be active; deactivating an agent clears this flag. "
            "Distinct from embed configuration."
        ),
    )
    call_recording_enabled: Optional[bool] = Field(
        None,
        description=(
            "Enable call recordings for this agent. Recording remains subject "
            "to the runtime recording feature gate."
        ),
    )
    is_demo: Optional[bool] = Field(
        None,
        description=(
            "Mark this agent as a demo agent that bypasses voice credit checks "
            "and is available on a dedicated public demo page. Platform-admin only."
        ),
    )
    demo_slug: Optional[str] = Field(
        None,
        max_length=100,
        description=(
            "Unique slug for the demo public page. Required when is_demo is true. "
            "Must be unique across all demo agents."
        ),
    )
    public_description: Optional[str] = Field(
        None,
        max_length=1000,
        description=(
            "Customer-facing description for the public demo page. Distinct from "
            "LLM prompt fields; shown to visitors before calling."
        ),
    )
    demo_public_result_url: Optional[str] = Field(
        None,
        max_length=2048,
        description=(
            "Optional HTTPS URL shown on a successful demo receipt as the "
            "public result destination. Platform-admin only."
        ),
    )
    demo_calls_remaining: Optional[int] = Field(
        None,
        ge=-1,
        description=(
            "Number of demo call reservations remaining. Zero disables new "
            "calls; -1 means unlimited. Platform-admin only."
        ),
    )
    demo_max_call_duration_seconds: Optional[int] = Field(
        None,
        ge=-1,
        description=(
            "Maximum duration for each demo call in seconds. A positive value "
            "caps the call; -1 means unlimited. Platform-admin only."
        ),
    )

    @field_validator("demo_slug", mode="before")
    @classmethod
    def validate_demo_slug_update(cls, v: Optional[str]) -> Optional[str]:
        """Normalize and validate demo slug on update."""
        if v is None or v == "":
            return None
        v = str(v).strip().lower()
        v = re.sub(r"\s+", "-", v)
        if not re.match(r"^[a-z0-9-]+$", v):
            raise ValueError(
                "Demo slug can only contain lowercase letters, numbers, and hyphens"
            )
        if len(v) < 2 or len(v) > 100:
            raise ValueError("Demo slug must be between 2 and 100 characters")
        return v

    @field_validator("public_description", mode="before")
    @classmethod
    def validate_public_description_update(cls, v: Optional[str]) -> Optional[str]:
        """Trim and validate public description on update."""
        if v is None or v == "":
            return None
        v = str(v).strip()
        if len(v) > 1000:
            raise ValueError("Public description must be at most 1000 characters")
        return v

    @field_validator("demo_public_result_url", mode="before")
    @classmethod
    def validate_demo_public_result_url_update(cls, v: Optional[str]) -> Optional[str]:
        """Trim and validate the optional demo receipt destination on update."""
        return normalize_demo_public_result_url(v)

    @field_validator("demo_max_call_duration_seconds")
    @classmethod
    def validate_demo_max_call_duration_update(cls, v: Optional[int]) -> Optional[int]:
        """Allow ``-1`` for unlimited or require a positive duration."""
        if v is not None and v != -1 and v <= 0:
            raise ValueError(
                "Demo max call duration must be -1 (unlimited) or greater than 0"
            )
        return v


class VoiceAgent(VoiceAgentBase):
    """Model for a voice agent with all attributes."""

    id: UUID = Field(..., description="Agent ID")
    organization_id: UUID = Field(..., description="Organization ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    # Note: system_prompt is auto-generated by PromptBuilder at runtime
    # based on organization context and agent configuration


class DeleteResponse(BaseModel):
    """Response model for delete operations."""

    id: UUID = Field(..., description="ID of deleted resource")
    success: bool = Field(..., description="Whether deletion was successful")
