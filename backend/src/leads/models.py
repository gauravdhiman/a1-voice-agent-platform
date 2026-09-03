"""Pydantic models for private interest-lead capture."""

from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class InterestLeadCreate(BaseModel):
    """Visitor-submitted interest (public, unauthenticated)."""

    name: str = Field(..., min_length=1, max_length=120, description="Contact name")
    business_name: Optional[str] = Field(
        None, max_length=160, description="Business name"
    )
    email: EmailStr = Field(..., description="Contact email address")
    phone: Optional[str] = Field(None, max_length=32, description="Callback number")
    vertical: Optional[str] = Field(
        None, max_length=40, description="Business vertical (dental, hvac, restaurant)"
    )
    message: Optional[str] = Field(
        None, max_length=2000, description="What the business needs"
    )
    source: Literal["request-demo", "outcome-form", "demo-call", "manual"] = Field(
        default="request-demo", description="Capture channel"
    )
    demo_slug: Optional[str] = Field(
        None, max_length=100, description="Demo agent slug when captured post-demo"
    )
    captcha_token: Optional[str] = Field(
        None,
        max_length=2048,
        description="Cloudflare Turnstile token (required when enforced)",
    )


class InterestLead(BaseModel):
    """Stored interest lead (platform-admin view)."""

    id: UUID
    name: str
    business_name: Optional[str] = None
    email: str
    phone: Optional[str] = None
    vertical: Optional[str] = None
    message: Optional[str] = None
    source: str
    demo_slug: Optional[str] = None
    status: str
    created_at: datetime
    contacted_at: Optional[datetime] = None


class InterestLeadAck(BaseModel):
    """Deliberately empty success envelope for public submission.

    Always returned, even for duplicates, so submitters cannot probe
    which emails already exist.
    """

    received: bool = Field(default=True, description="Submission accepted")
