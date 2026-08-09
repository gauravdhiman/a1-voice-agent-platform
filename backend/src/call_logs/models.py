"""Pydantic models for call log functionality."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


class CallLog(BaseModel):
    """A single call log entry."""

    id: UUID
    call_sid: str
    organization_id: UUID
    agent_id: Optional[UUID]
    caller_number: Optional[str]
    called_number: Optional[str]
    status: str
    duration: Optional[int] = None
    credits_consumed: int = 0
    credit_transaction_id: Optional[UUID] = None
    recording_available: bool = False
    started_at: Optional[datetime]
    ended_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class CallLogCreate(BaseModel):
    """Data needed to create a call log entry."""

    call_sid: str
    organization_id: UUID
    agent_id: Optional[UUID] = None
    caller_number: Optional[str] = None
    called_number: Optional[str] = None
    status: str = "initiated"
    duration: int = 0
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None


class CallLogUpdate(BaseModel):
    """Fields that can be updated on a call log."""

    status: Optional[str] = None
    duration: Optional[int] = None
    ended_at: Optional[datetime] = None


class CallLogsResponse(BaseModel):
    """Paginated call logs response."""

    items: List[CallLog]
    total: int
    page: int
    page_size: int
    total_pages: int


class CallAnalytics(BaseModel):
    """Analytics summary for calls."""

    total_calls_week: int
    total_calls_month: int
    avg_duration_seconds: float
    calls_by_agent: List[dict]
    calls_by_hour: List[dict]
    calls_by_status: List[dict]
