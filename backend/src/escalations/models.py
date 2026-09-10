"""Pydantic models for owner-visible callback escalations."""

from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class EscalationCreate(BaseModel):
    """Manually logged callback request (org admins only)."""

    caller_phone: str = Field(
        ..., min_length=7, max_length=32, description="Callback number"
    )
    reason: str = Field(
        ..., min_length=1, max_length=500, description="What the callback is about"
    )
    urgency: Literal["normal", "urgent"] = Field(
        default="normal", description="Callback urgency"
    )
    caller_name: Optional[str] = Field(
        None, max_length=100, description="Caller name when known"
    )
    agent_id: Optional[UUID] = Field(
        None, description="Agent that would have handled the call"
    )
    session_id: Optional[str] = Field(
        None, max_length=100, description="Voice session identifier when known"
    )


class EscalationStatusUpdate(BaseModel):
    """Follow-up status transition for one escalation."""

    status: Literal["new", "acknowledged", "resolved"] = Field(
        ..., description="Target follow-up status"
    )


class Escalation(BaseModel):
    """Stored callback escalation (org-member view)."""

    id: UUID
    organization_id: UUID
    agent_id: Optional[UUID] = None
    session_id: Optional[str] = None
    caller_phone: str
    caller_name: Optional[str] = None
    reason: str
    urgency: str
    status: str
    notified: bool
    created_at: datetime
    acknowledged_at: Optional[datetime] = None
