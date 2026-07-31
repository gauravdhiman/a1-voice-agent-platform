"""
Pydantic models for Organization functionality shared across backend and worker.
"""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class OrganizationBase(BaseModel):
    """Base model for Organization."""

    name: str = Field(
        ..., min_length=1, max_length=100, description="Organization name"
    )
    description: Optional[str] = Field(
        None, max_length=500, description="Organization description"
    )
    slug: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Organization slug (unique identifier)",
    )
    website: Optional[str] = Field(None, description="Organization website URL")
    is_active: bool = Field(
        default=True, description="Whether the organization is active"
    )
    industry: Optional[str] = Field(
        None, max_length=100, description="Industry of the organization"
    )
    location: Optional[str] = Field(
        None, max_length=255, description="Physical address or location"
    )
    business_details: Optional[str] = Field(
        None,
        description="""
        Comprehensive business context for AI agent system prompts.
        
        Include information such as:
        - Products and services offered
        - Business hours (including special schedules, holidays, seasonal variations)
        - Service areas and location details
        - Company policies and procedures
        - Unique selling points and differentiators
        - Common customer questions and how to handle them
        - Emergency or after-hours protocols
        - Any other context helps the AI represent your business accurately
        
        This information is used to construct the AI agent's system prompt
        and will be referenced when interacting with callers.
        """,
    )
    google_api_key: Optional[str] = Field(
        None,
        description="""
        Organization's own Google API key for voice agents.

        If set, voice agents can use this API key instead of the platform key,
        allowing billing to go directly to the organization's Google Cloud project.
        The key is stored encrypted and decrypted only when needed.
        """,
    )
    provider_credentials: Optional[str] = Field(
        None,
        description=(
            "Fernet-encrypted JSON blob of all per-org provider keys via "
            "encrypt_data/decrypt_data: {google, deepgram, openai, cartesia, "
            "cerebras, livekit: {api_key, api_secret}} (only the set keys "
            "present). Source of truth for the worker's key resolver; the "
            "legacy plaintext google_api_key column is retained but unused. "
            "Returned as the opaque encrypted string; never expose decrypted "
            "values to the frontend."
        ),
    )
    public_page_enabled: bool = Field(
        default=False,
        description=(
            "When true, the organization has a public showcase page at "
            "/o/{slug} listing agents published for public calls."
        ),
    )
    public_page_passphrase_enabled: bool = Field(
        default=False,
        description=(
            "When true, visitors must supply the org passphrase before viewing "
            "published agents on the public page."
        ),
    )


class OrganizationCreate(OrganizationBase):
    """Model for creating a new organization."""

    pass


class OrganizationUpdate(BaseModel):
    """Model for updating an organization."""

    name: Optional[str] = Field(
        None, min_length=1, max_length=100, description="Organization name"
    )
    description: Optional[str] = Field(
        None, max_length=500, description="Organization description"
    )
    slug: Optional[str] = Field(
        None,
        min_length=1,
        max_length=100,
        description="Organization slug (unique identifier)",
    )
    website: Optional[str] = Field(None, description="Organization website URL")
    is_active: Optional[bool] = Field(
        None, description="Whether the organization is active"
    )
    industry: Optional[str] = Field(
        None, max_length=100, description="Industry of the organization"
    )
    location: Optional[str] = Field(
        None, max_length=255, description="Physical address or location"
    )
    business_details: Optional[str] = Field(
        None,
        description="""
        Comprehensive business context for AI agent system prompts.
        
        Include information such as:
        - Products and services offered
        - Business hours (including special schedules, holidays, seasonal variations)
        - Service areas and location details
        - Company policies and procedures
        - Unique selling points and differentiators
        - Common customer questions and how to handle them
        - Emergency or after-hours protocols
        - Any other context that helps the AI represent your business accurately
        
        This information is used to construct the AI agent's system prompt
        and will be referenced when interacting with callers.
        """,
    )
    google_api_key: Optional[str] = Field(
        None,
        description="""
        Organization's own Google API key for voice agents.

        If set, voice agents can use this API key instead of the platform key,
        allowing billing to go directly to the organization's Google Cloud project.
        """,
    )
    provider_credentials_input: Optional[Dict[str, Any]] = Field(
        None,
        exclude=True,
        description=(
            "Plaintext per-org provider credentials supplied from the UI, e.g. "
            "{'google': '...', 'openai': '...', 'livekit': {'api_key': '...', "
            "'api_secret': '...'}}. The service merges this with any existing "
            "decrypted credentials and re-encrypts the whole blob into "
            "provider_credentials; this field is NEVER persisted directly. The "
            "legacy google_api_key field is still accepted and routed into "
            "provider_credentials['google'] for back-compat with the existing UI."
        ),
    )
    public_page_enabled: Optional[bool] = Field(
        None,
        description="Enable the public organization showcase page at /o/{slug}.",
    )
    public_page_passphrase_enabled: Optional[bool] = Field(
        None,
        description="Require a passphrase before visitors can view public agents.",
    )
    public_page_passphrase: Optional[str] = Field(
        None,
        exclude=True,
        description=(
            "Plaintext passphrase to set or rotate. Empty string clears the "
            "passphrase hash. Never returned on read."
        ),
    )


class Organization(OrganizationBase):
    """Model for an organization with all attributes."""

    id: UUID = Field(..., description="Organization ID")
    onboarding_completed: bool = Field(
        default=False, description="Whether the onboarding wizard has been completed"
    )
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    provider_credentials_status: Optional[Dict[str, bool]] = Field(
        default=None,
        description=(
            "Per-provider 'is a key configured?' map (booleans only — never the "
            "decrypted values), derived from the encrypted provider_credentials "
            "blob on read: {google, deepgram, openai, cartesia, cerebras, "
            "livekit}. Surfaced so the org-settings UI can show "
            "Configured/Not-configured pills per provider without exposing "
            "secrets to the frontend. Read-only; not an input field."
        ),
    )
