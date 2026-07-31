"""
Pydantic models for Voice Agent functionality.
"""

import re
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


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

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, v: Optional[str]) -> Optional[str]:
        """Validate E.164 phone number format."""
        if v is None or v == "":
            return None
        # E.164 format requires country code (1-3 digits) + subscriber number
        # Minimum 8 characters total (including +) for valid international numbers
        if not re.match(r"^\+[1-9]\d{7,14}$", v):
            raise ValueError(
                "Phone number must be in E.164 format "
                "with at least 8 digits "
                "(e.g., +14155551234 or +441632960000)"
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
