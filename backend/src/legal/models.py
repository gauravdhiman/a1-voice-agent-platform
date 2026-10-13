"""Legal document versioning models for Terms & Conditions and Privacy Policy.

Documents are stored as Markdown and versioned like billing plan versions:
published rows are immutable, one draft per document key, and one published
version per key is marked current. Acceptance rows bind each user to the exact
version they accepted at signup or OAuth handoff.
"""

from datetime import datetime
from enum import Enum
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field

LegalDocumentKey = Literal["terms", "privacy"]

LEGAL_DOCUMENT_TITLES: dict[str, str] = {
    "terms": "Terms & Conditions",
    "privacy": "Privacy Policy",
}


class LegalVersionStatus(str, Enum):
    """Lifecycle status for a legal document version row."""

    DRAFT = "draft"
    PUBLISHED = "published"
    DEPRECATED = "deprecated"
    RETIRED = "retired"


class LegalDocumentPublic(BaseModel):
    """Latest published document rendered on the public site."""

    document_key: str
    title: str
    version_number: int
    content_markdown: str
    published_at: Optional[datetime] = None


class LegalDocumentVersionSummary(BaseModel):
    """Version history row metadata without document content."""

    id: UUID
    document_key: str
    version_number: int
    status: LegalVersionStatus
    is_current: bool
    summary_of_changes: Optional[str] = None
    published_at: Optional[datetime] = None
    published_by: Optional[UUID] = None
    created_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime


class LegalDocumentVersionDetail(LegalDocumentVersionSummary):
    """Full version row including document content."""

    content_markdown: str


class LegalDraftCreate(BaseModel):
    """Request body for creating the next draft of a document."""

    content_markdown: Optional[str] = Field(
        default=None,
        description="Draft content; copies the current published text when omitted",
    )
    summary_of_changes: Optional[str] = Field(default=None, max_length=2000)


class LegalDraftUpdate(BaseModel):
    """Request body for editing an existing draft."""

    content_markdown: str = Field(..., min_length=1)
    summary_of_changes: Optional[str] = Field(default=None, max_length=2000)


class LegalPublishRequest(BaseModel):
    """Request body for publishing a draft legal document version."""

    notify_users: bool = Field(
        default=True,
        description="Queue an update email for every previously signed-up user",
    )


class LegalPublishResult(BaseModel):
    """Result returned after a successful legal document publish."""

    version: LegalDocumentVersionDetail
    publish_event_id: UUID
    notified_count: int
    dispatch_id: Optional[UUID] = None
