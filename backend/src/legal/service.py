"""Legal document versioning, acceptance capture, and publish notification.

Mirrors the billing ``plan_versions`` draft/publish contract: published versions
are immutable, one draft per ``document_key``, and one published version per key
is marked current. Publishing optionally enqueues a durable per-user email outbox
drained by the notification retry scheduler.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID, uuid4

from shared.config import supabase_config

from .models import (
    LEGAL_DOCUMENT_TITLES,
    LegalDocumentPublic,
    LegalDocumentVersionDetail,
    LegalDocumentVersionSummary,
    LegalPublishRequest,
    LegalPublishResult,
    LegalVersionStatus,
)

logger = logging.getLogger(__name__)

VERSIONS_TABLE = "legal_document_versions"
PUBLISH_EVENTS_TABLE = "legal_document_publish_events"
ACCEPTANCES_TABLE = "legal_document_acceptances"
OUTBOX_TABLE = "legal_update_notification_outbox"

MAX_USER_PAGES = 200
USERS_PER_PAGE = 200


class LegalDocumentService:
    """Manage legal document versions, user acceptance, and publish dispatch."""

    def __init__(self) -> None:
        """Initialize with the service-role Supabase client."""
        self._supabase_config = supabase_config

    @property
    def supabase(self):
        """Return the Supabase client used for service-role database access."""
        return self._supabase_config.service_client or self._supabase_config.client

    # ------------------------------------------------------------------
    # Public reads
    # ------------------------------------------------------------------

    async def get_published_document(self, document_key: str) -> LegalDocumentPublic:
        """Return the current published version of a legal document.

        Args:
            document_key: ``terms`` or ``privacy``.

        Returns:
            LegalDocumentPublic with the current published content.

        Raises:
            ValueError: When no published version exists for the document key.
        """
        row = await self._get_current_published_row(document_key)
        if not row:
            raise ValueError(f"No published {document_key} document")
        return LegalDocumentPublic(
            document_key=row["document_key"],
            title=LEGAL_DOCUMENT_TITLES.get(row["document_key"], row["document_key"]),
            version_number=int(row["version_number"]),
            content_markdown=row["content_markdown"],
            published_at=row.get("published_at"),
        )

    # ------------------------------------------------------------------
    # Admin reads
    # ------------------------------------------------------------------

    async def list_versions(
        self, document_key: str
    ) -> list[LegalDocumentVersionSummary]:
        """List all versions of a document, newest version number first."""
        result = (
            self.supabase.table(VERSIONS_TABLE)
            .select("*")
            .eq("document_key", document_key)
            .order("version_number", desc=True)
            .execute()
        )
        return [self._to_summary(row) for row in (result.data or [])]

    async def get_version(self, version_id: UUID) -> LegalDocumentVersionDetail:
        """Fetch one version row including its content.

        Raises:
            ValueError: When the version does not exist.
        """
        row = await self._get_version_row(version_id)
        return self._to_detail(row)

    # ------------------------------------------------------------------
    # Draft lifecycle
    # ------------------------------------------------------------------

    async def create_draft(
        self,
        document_key: str,
        *,
        content_markdown: Optional[str] = None,
        summary_of_changes: Optional[str] = None,
        created_by: Optional[UUID] = None,
    ) -> LegalDocumentVersionDetail:
        """Create the next draft version for a document key.

        Copies the current published content when ``content_markdown`` is omitted
        so admins edit from a known baseline.

        Args:
            document_key: ``terms`` or ``privacy``.
            content_markdown: Draft content, defaults to the current published text.
            summary_of_changes: Optional change summary shown in version history.
            created_by: Platform admin creating the draft.

        Returns:
            The created draft as a version detail.

        Raises:
            ValueError: When a draft already exists for the document key.
        """
        existing_draft = await self._get_draft_row(document_key)
        if existing_draft:
            raise ValueError(
                f"A draft version of '{document_key}' already exists. "
                "Edit or publish that draft before creating another."
            )

        content = content_markdown
        if content is None:
            current = await self._get_current_published_row(document_key)
            content = current["content_markdown"] if current else ""

        now = datetime.now(timezone.utc).isoformat()
        row = {
            "document_key": document_key,
            "version_number": await self._next_version_number(document_key),
            "status": LegalVersionStatus.DRAFT.value,
            "content_markdown": content,
            "summary_of_changes": summary_of_changes,
            "is_current": False,
            "created_by": str(created_by) if created_by else None,
            "created_at": now,
            "updated_at": now,
        }
        result = self.supabase.table(VERSIONS_TABLE).insert(row).execute()
        inserted = (result.data or [None])[0]
        if not inserted:
            raise ValueError(f"Failed to create draft for '{document_key}'")
        return self._to_detail(inserted)

    async def update_draft(
        self,
        version_id: UUID,
        *,
        content_markdown: str,
        summary_of_changes: Optional[str] = None,
    ) -> LegalDocumentVersionDetail:
        """Update the content of an existing draft version.

        Raises:
            ValueError: When the version is missing or is not a draft.
        """
        row = await self._get_version_row(version_id)
        if row.get("status") != LegalVersionStatus.DRAFT.value:
            raise ValueError(
                f"Version {version_id} is not a draft (status={row.get('status')})"
            )

        fields: dict[str, Any] = {
            "content_markdown": content_markdown,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if summary_of_changes is not None:
            fields["summary_of_changes"] = summary_of_changes

        updated = (
            self.supabase.table(VERSIONS_TABLE)
            .update(fields)
            .eq("id", str(version_id))
            .execute()
        )
        updated_row = (updated.data or [None])[0]
        if not updated_row:
            raise ValueError(f"Failed to update draft version {version_id}")
        return self._to_detail(updated_row)

    async def delete_draft(self, version_id: UUID) -> None:
        """Delete a draft version.

        Raises:
            ValueError: When the version is missing or is not a draft.
        """
        row = await self._get_version_row(version_id)
        if row.get("status") != LegalVersionStatus.DRAFT.value:
            raise ValueError(
                f"Version {version_id} is not a draft (status={row.get('status')})"
            )
        self.supabase.table(VERSIONS_TABLE).delete().eq("id", str(version_id)).execute()

    # ------------------------------------------------------------------
    # Publish
    # ------------------------------------------------------------------

    async def publish_version(
        self,
        version_id: UUID,
        request: LegalPublishRequest,
        published_by: UUID,
    ) -> LegalPublishResult:
        """Publish a draft version and optionally queue user update emails.

        The predecessor current version is deprecated first so the
        single-current partial unique index is never violated mid-publish.

        Args:
            version_id: UUID of the draft version to publish.
            request: Publish options including ``notify_users``.
            published_by: Platform admin performing the publish.

        Returns:
            LegalPublishResult with the published version and notification counts.

        Raises:
            ValueError: When the version is missing or is not a draft.
        """
        draft = await self._get_version_row(version_id)
        if draft.get("status") != LegalVersionStatus.DRAFT.value:
            raise ValueError(
                f"Version {version_id} is not a draft (status={draft.get('status')})"
            )

        document_key = draft["document_key"]
        version_number = int(draft["version_number"])
        previous = await self._get_current_published_row(document_key)
        previous_version_id = UUID(str(previous["id"])) if previous else None
        published_at = datetime.now(timezone.utc)

        # Demote the predecessor first: ux_legal_document_versions_single_current
        # permits only one is_current row per document_key.
        if previous_version_id and previous_version_id != version_id:
            self.supabase.table(VERSIONS_TABLE).update(
                {
                    "is_current": False,
                    "status": LegalVersionStatus.DEPRECATED.value,
                    "updated_at": published_at.isoformat(),
                }
            ).eq("id", str(previous_version_id)).execute()

        self.supabase.table(VERSIONS_TABLE).update(
            {
                "status": LegalVersionStatus.PUBLISHED.value,
                "is_current": True,
                "published_at": published_at.isoformat(),
                "published_by": str(published_by),
                "updated_at": published_at.isoformat(),
            }
        ).eq("id", str(version_id)).execute()

        dispatch_id: Optional[UUID] = None
        notified_count = 0
        if request.notify_users:
            dispatch_id = uuid4()
            notified_count = await self._enqueue_user_notifications(
                dispatch_id=dispatch_id,
                version_id=version_id,
                document_key=document_key,
                version_number=version_number,
                summary_of_changes=draft.get("summary_of_changes"),
                published_at=published_at,
            )

        event_result = (
            self.supabase.table(PUBLISH_EVENTS_TABLE)
            .insert(
                {
                    "legal_document_version_id": str(version_id),
                    "document_key": document_key,
                    "version_number": version_number,
                    "previous_legal_document_version_id": (
                        str(previous_version_id) if previous_version_id else None
                    ),
                    "notify_users": request.notify_users,
                    "notified_count": notified_count,
                    "dispatch_id": str(dispatch_id) if dispatch_id else None,
                    "published_by": str(published_by),
                    "published_at": published_at.isoformat(),
                }
            )
            .execute()
        )
        event_row = (event_result.data or [None])[0]
        if not event_row:
            raise ValueError(f"Failed to record publish event for version {version_id}")

        logger.info(
            "Published legal document %s v%s (previous=%s, notified=%s)",
            document_key,
            version_number,
            previous_version_id,
            notified_count,
        )

        updated_row = await self._get_version_row(version_id)
        return LegalPublishResult(
            version=self._to_detail(updated_row),
            publish_event_id=UUID(str(event_row["id"])),
            notified_count=notified_count,
            dispatch_id=dispatch_id,
        )

    async def _enqueue_user_notifications(
        self,
        *,
        dispatch_id: UUID,
        version_id: UUID,
        document_key: str,
        version_number: int,
        summary_of_changes: Optional[str],
        published_at: datetime,
    ) -> int:
        """Queue one outbox row per user who signed up before the publish.

        Users are enumerated through the Supabase admin API; users without an
        email or created after the publish timestamp are skipped.

        Returns:
            Number of outbox rows enqueued.
        """
        recipients = await self._list_recipients_before(published_at)
        if not recipients:
            return 0

        rows = [
            {
                "dispatch_id": str(dispatch_id),
                "legal_document_version_id": str(version_id),
                "document_key": document_key,
                "version_number": version_number,
                "user_id": recipient["user_id"],
                "recipient_email": recipient["email"],
                "recipient_name": recipient.get("name"),
                "summary_of_changes": summary_of_changes,
            }
            for recipient in recipients
        ]
        try:
            self.supabase.table(OUTBOX_TABLE).insert(rows).execute()
        except Exception as error:
            logger.error(
                "Failed to enqueue legal update notifications for %s v%s: %s",
                document_key,
                version_number,
                error,
                exc_info=True,
            )
            return 0
        return len(rows)

    async def _list_recipients_before(
        self, cutoff: datetime
    ) -> list[dict[str, Optional[str]]]:
        """Enumerate auth users created before ``cutoff`` with an email."""
        recipients: list[dict[str, Optional[str]]] = []
        for page in range(1, MAX_USER_PAGES + 1):
            try:
                response = self.supabase.auth.admin.list_users(
                    page=page, per_page=USERS_PER_PAGE
                )
            except Exception as error:
                logger.error("Failed to list users for legal update: %s", error)
                break

            users_list: list[Any] = []
            if hasattr(response, "users"):
                users_list = response.users or []
            elif isinstance(response, list):
                users_list = response

            for user in users_list:
                email = getattr(user, "email", None)
                if not email:
                    continue
                created_at = self._parse_datetime(getattr(user, "created_at", None))
                if created_at and created_at >= cutoff:
                    continue
                user_id = getattr(user, "id", None)
                if not user_id:
                    continue
                metadata = getattr(user, "user_metadata", None) or {}
                name = (
                    " ".join(
                        part
                        for part in (
                            str(metadata.get("first_name") or "").strip(),
                            str(metadata.get("last_name") or "").strip(),
                        )
                        if part
                    )
                    or None
                )
                recipients.append(
                    {
                        "user_id": str(user_id),
                        "email": str(email),
                        "name": name,
                    }
                )

            if len(users_list) < USERS_PER_PAGE:
                break
        return recipients

    # ------------------------------------------------------------------
    # Acceptance capture
    # ------------------------------------------------------------------

    async def record_user_acceptance(
        self,
        user_id: UUID,
        *,
        source: str,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> int:
        """Record acceptance of every current published document version.

        One row is written per currently published document (terms and privacy)
        for the user. The insert is idempotent on
        ``(user_id, document_key, version_number)`` so repeated sign-in handoffs
        never create duplicates. Documents without a published version are
        skipped so a fresh database does not block signup.

        Args:
            user_id: User accepting the documents.
            source: ``signup``, ``oauth``, or ``reaccept``.
            user_agent: Optional request user agent for audit.
            ip_address: Optional request IP for audit.

        Returns:
            Number of acceptance rows created.
        """
        created = 0
        for document_key in LEGAL_DOCUMENT_TITLES:
            current = await self._get_current_published_row(document_key)
            if not current:
                continue
            try:
                result = (
                    self.supabase.table(ACCEPTANCES_TABLE)
                    .upsert(
                        {
                            "user_id": str(user_id),
                            "document_key": document_key,
                            "legal_document_version_id": str(current["id"]),
                            "version_number": int(current["version_number"]),
                            "source": source,
                            "user_agent": user_agent,
                            "ip_address": ip_address,
                        },
                        on_conflict="user_id,document_key,version_number",
                        ignore_duplicates=True,
                    )
                    .execute()
                )
                created += len(result.data or [])
            except Exception as error:
                logger.error(
                    "Failed to record legal acceptance for user %s (%s): %s",
                    user_id,
                    document_key,
                    error,
                    exc_info=True,
                )
        return created

    # ------------------------------------------------------------------
    # Row helpers
    # ------------------------------------------------------------------

    async def _get_version_row(self, version_id: UUID) -> dict[str, Any]:
        """Fetch a version row by primary key."""
        result = (
            self.supabase.table(VERSIONS_TABLE)
            .select("*")
            .eq("id", str(version_id))
            .single()
            .execute()
        )
        if not result.data:
            raise ValueError(f"Legal document version {version_id} not found")
        return result.data

    async def _get_current_published_row(
        self, document_key: str
    ) -> Optional[dict[str, Any]]:
        """Return the version currently marked published and current."""
        result = (
            self.supabase.table(VERSIONS_TABLE)
            .select("*")
            .eq("document_key", document_key)
            .eq("status", LegalVersionStatus.PUBLISHED.value)
            .eq("is_current", True)
            .limit(1)
            .execute()
        )
        rows = result.data or []
        return rows[0] if rows else None

    async def _get_draft_row(self, document_key: str) -> Optional[dict[str, Any]]:
        """Return the open draft for a document key, if any."""
        result = (
            self.supabase.table(VERSIONS_TABLE)
            .select("*")
            .eq("document_key", document_key)
            .eq("status", LegalVersionStatus.DRAFT.value)
            .limit(1)
            .execute()
        )
        rows = result.data or []
        return rows[0] if rows else None

    async def _next_version_number(self, document_key: str) -> int:
        """Return the next version number for a document key."""
        result = (
            self.supabase.table(VERSIONS_TABLE)
            .select("version_number")
            .eq("document_key", document_key)
            .order("version_number", desc=True)
            .limit(1)
            .execute()
        )
        rows = result.data or []
        if not rows:
            return 1
        return int(rows[0]["version_number"]) + 1

    @staticmethod
    def _parse_datetime(value: Any) -> Optional[datetime]:
        """Parse an ISO-8601 timestamp string into an aware datetime."""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)

    @classmethod
    def _to_summary(cls, row: dict[str, Any]) -> LegalDocumentVersionSummary:
        """Convert a raw row to a version summary model."""
        return LegalDocumentVersionSummary(
            id=UUID(str(row["id"])),
            document_key=row["document_key"],
            version_number=int(row["version_number"]),
            status=row["status"],
            is_current=bool(row.get("is_current")),
            summary_of_changes=row.get("summary_of_changes"),
            published_at=cls._parse_datetime(row.get("published_at")),
            published_by=(
                UUID(str(row["published_by"])) if row.get("published_by") else None
            ),
            created_by=(
                UUID(str(row["created_by"])) if row.get("created_by") else None
            ),
            created_at=cls._parse_datetime(row.get("created_at")),
            updated_at=cls._parse_datetime(row.get("updated_at")),
        )

    @classmethod
    def _to_detail(cls, row: dict[str, Any]) -> LegalDocumentVersionDetail:
        """Convert a raw row to a version detail model."""
        summary = cls._to_summary(row)
        return LegalDocumentVersionDetail(
            **summary.model_dump(), content_markdown=row["content_markdown"]
        )


legal_service = LegalDocumentService()
