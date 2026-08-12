"""
Notification service for sending and managing email notifications.
"""

import html
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from src.notifications.email_providers import (
    EmailMessage,
    EmailProvider,
    build_email_provider,
)
from src.notifications.models import (
    NotificationEvent,
    NotificationEventCreate,
    NotificationEventUpdate,
    NotificationLog,
    NotificationLogCreate,
    NotificationProvider,
    NotificationStats,
    NotificationStatus,
    NotificationTemplate,
    NotificationTemplateCreate,
    NotificationTemplateUpdate,
    SendNotificationRequest,
    SendNotificationResponse,
)
from src.notifications.templates import TEMPLATE_REGISTRY, get_template_html

from shared.config import settings, supabase_config

logger = logging.getLogger(__name__)

RETRY_DELAY_MINUTES = 5


@dataclass
class NotificationRetryResult:
    """Counters returned by one failed/pending notification retry pass."""

    processed: int = 0
    succeeded: int = 0
    failed: int = 0
    skipped: int = 0


def validate_template_variables(
    required_variables: List[str],
    template_variables: Optional[Dict[str, Any]],
    apply_defaults: bool = True,
) -> Dict[str, Any]:
    """
    Validate that required template variables are provided.
    Optionally apply default app-level variables before validation.

    Args:
        required_variables: List of required variable names
        template_variables: The variables provided for the template
        apply_defaults: Whether to apply default app-level variables

    Returns:
        Dict of validated variables with defaults applied (if requested)

    Raises:
        ValueError: If required variables are missing
    """
    if not template_variables:
        template_variables = {}

    # Apply default app-level variables if requested
    all_vars = template_variables.copy()
    if apply_defaults:
        from shared.config import settings

        default_vars = {
            "app_name": settings.app_name,
            "app_url": settings.app_base_url,
            "support_url": f"{settings.app_base_url}/support",
            "unsubscribe_url": f"{settings.app_base_url}/unsubscribe",
        }
        # Merge defaults with provided variables (provided variables take precedence)
        all_vars = {**default_vars, **template_variables}

    # Check for missing required variables
    missing_variables = []
    for var in required_variables:
        if var not in all_vars:
            missing_variables.append(var)

    if missing_variables:
        raise ValueError(
            f"Missing required template variables: {', '.join(missing_variables)}"
        )

    # Return the required validated variables with defaults applied (if requested)
    return all_vars


def validate_builtin_template_variables(
    event_key: str, template_variables: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Validate that required template variables are provided for the given built-in event.
    Apply default app-level variables before validation to ensure common variables
    are available for validation.

    Args:
        event_key: The event key for which to validate variables
        template_variables: The variables provided for the template

    Returns:
        Dict of validated variables with defaults applied

    Raises:
        ValueError: If required variables are missing
    """
    # Get the template definition from registry
    template_data = TEMPLATE_REGISTRY.get(event_key)
    if not template_data:
        raise ValueError(f"No template found for event: {event_key}")

    required_variables = template_data.get("variables", [])

    # Validate with defaults applied
    return validate_template_variables(required_variables, template_variables)


def sanitize_template_variables(template_variables: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize template variables to prevent XSS and other injection attacks.

    Args:
        template_variables: The variables to sanitize

    Returns:
        Sanitized variables
    """
    sanitized = {}
    for key, value in template_variables.items():
        # Convert to string and sanitize HTML
        str_value = str(value)
        sanitized[key] = html.escape(str_value)
    return sanitized


class NotificationService:
    """Service for managing notifications."""

    def __init__(self, email_provider: Optional[EmailProvider] = None):
        self.supabase_config = supabase_config
        self.from_email = settings.resend_from_email
        self.from_name = settings.resend_from_name
        self.email_provider = email_provider or build_email_provider()

    @property
    def supabase(self):
        """Get Supabase client, raise error if not configured."""
        if not self.supabase_config.is_configured():
            logger.error(
                "Supabase is not configured. Please set SUPABASE_URL and SUPABASE_SERVICE_KEY."
            )
            raise ValueError(
                "Supabase is not configured. Please set SUPABASE_URL and SUPABASE_SERVICE_KEY."
            )
        return self.supabase_config.client

    # Notification Events Management

    async def create_notification_event(
        self, event_data: NotificationEventCreate
    ) -> NotificationEvent:
        """Create a new notification event."""
        try:
            response = (
                self.supabase.table("notification_events")
                .insert(
                    {
                        "name": event_data.name,
                        "description": event_data.description,
                        "event_key": event_data.event_key,
                        "category": event_data.category.value,
                        "is_enabled": event_data.is_enabled,
                        "default_template_id": (
                            str(event_data.default_template_id)
                            if event_data.default_template_id
                            else None
                        ),
                        "metadata": event_data.metadata,
                    }
                )
                .execute()
            )

            return NotificationEvent(**response.data[0])
        except Exception as e:
            logger.error(f"Error creating notification event: {e}")
            raise

    async def get_notification_event(
        self, event_id: UUID
    ) -> Optional[NotificationEvent]:
        """Get a notification event by ID."""
        try:
            response = (
                self.supabase.table("notification_events")
                .select("*")
                .eq("id", str(event_id))
                .single()
                .execute()
            )
            return NotificationEvent(**response.data) if response.data else None
        except Exception as e:
            logger.error(f"Error fetching notification event: {e}")
            return None

    async def get_notification_event_by_key(
        self, event_key: str
    ) -> Optional[NotificationEvent]:
        """Get a notification event by event key."""
        try:
            response = (
                self.supabase.table("notification_events")
                .select("*")
                .eq("event_key", event_key)
                .single()
                .execute()
            )
            return NotificationEvent(**response.data) if response.data else None
        except Exception as e:
            logger.error(f"Error fetching notification event by key: {e}")
            return None

    async def list_notification_events(
        self, category: Optional[str] = None, is_enabled: Optional[bool] = None
    ) -> List[NotificationEvent]:
        """List notification events with optional filters."""
        try:
            query = self.supabase.table("notification_events").select("*")

            if category:
                query = query.eq("category", category)
            if is_enabled is not None:
                query = query.eq("is_enabled", is_enabled)

            response = query.order("created_at", desc=True).execute()
            return [NotificationEvent(**item) for item in response.data]
        except Exception as e:
            logger.error(f"Error listing notification events: {e}")
            return []

    async def update_notification_event(
        self, event_id: UUID, event_data: NotificationEventUpdate
    ) -> Optional[NotificationEvent]:
        """Update a notification event."""
        try:
            update_data = {}
            if event_data.name is not None:
                update_data["name"] = event_data.name
            if event_data.description is not None:
                update_data["description"] = event_data.description
            if event_data.category is not None:
                update_data["category"] = event_data.category.value
            if event_data.is_enabled is not None:
                update_data["is_enabled"] = event_data.is_enabled
            if event_data.default_template_id is not None:
                update_data["default_template_id"] = str(event_data.default_template_id)
            if event_data.metadata is not None:
                update_data["metadata"] = event_data.metadata

            update_data["updated_at"] = datetime.now(timezone.utc).isoformat()

            response = (
                self.supabase.table("notification_events")
                .update(update_data)
                .eq("id", str(event_id))
                .execute()
            )
            return NotificationEvent(**response.data[0]) if response.data else None
        except Exception as e:
            logger.error(f"Error updating notification event: {e}")
            raise

    async def delete_notification_event(self, event_id: UUID) -> bool:
        """Delete a notification event."""
        try:
            self.supabase.table("notification_events").delete().eq(
                "id", str(event_id)
            ).execute()
            return True
        except Exception as e:
            logger.error(f"Error deleting notification event: {e}")
            return False

    # Notification Templates Management

    async def create_notification_template(
        self, template_data: NotificationTemplateCreate
    ) -> NotificationTemplate:
        """Create a new notification template."""
        try:
            response = (
                self.supabase.table("notification_templates")
                .insert(
                    {
                        "name": template_data.name,
                        "description": template_data.description,
                        "subject": template_data.subject,
                        "html_content": template_data.html_content,
                        "text_content": template_data.text_content,
                        "from_email": template_data.from_email,
                        "from_name": template_data.from_name,
                        "template_variables": template_data.template_variables,
                        "is_active": template_data.is_active,
                    }
                )
                .execute()
            )

            return NotificationTemplate(**response.data[0])
        except Exception as e:
            logger.error(f"Error creating notification template: {e}")
            raise

    async def get_notification_template(
        self, template_id: UUID
    ) -> Optional[NotificationTemplate]:
        """Get a notification template by ID."""
        try:
            response = (
                self.supabase.table("notification_templates")
                .select("*")
                .eq("id", str(template_id))
                .single()
                .execute()
            )
            return NotificationTemplate(**response.data) if response.data else None
        except Exception as e:
            logger.error(f"Error fetching notification template: {e}")
            return None

    async def list_notification_templates(
        self, is_active: Optional[bool] = None
    ) -> List[NotificationTemplate]:
        """List notification templates with optional filters."""
        try:
            query = self.supabase.table("notification_templates").select("*")

            if is_active is not None:
                query = query.eq("is_active", is_active)

            response = query.order("created_at", desc=True).execute()
            return [NotificationTemplate(**item) for item in response.data]
        except Exception as e:
            logger.error(f"Error listing notification templates: {e}")
            return []

    async def update_notification_template(
        self, template_id: UUID, template_data: NotificationTemplateUpdate
    ) -> Optional[NotificationTemplate]:
        """Update a notification template."""
        try:
            update_data = {}
            if template_data.name is not None:
                update_data["name"] = template_data.name
            if template_data.description is not None:
                update_data["description"] = template_data.description
            if template_data.subject is not None:
                update_data["subject"] = template_data.subject
            if template_data.html_content is not None:
                update_data["html_content"] = template_data.html_content
            if template_data.text_content is not None:
                update_data["text_content"] = template_data.text_content
            if template_data.from_email is not None:
                update_data["from_email"] = template_data.from_email
            if template_data.from_name is not None:
                update_data["from_name"] = template_data.from_name
            if template_data.template_variables is not None:
                update_data["template_variables"] = template_data.template_variables
            if template_data.is_active is not None:
                update_data["is_active"] = template_data.is_active

            update_data["updated_at"] = datetime.now(timezone.utc).isoformat()

            response = (
                self.supabase.table("notification_templates")
                .update(update_data)
                .eq("id", str(template_id))
                .execute()
            )
            return NotificationTemplate(**response.data[0]) if response.data else None
        except Exception as e:
            logger.error(f"Error updating notification template: {e}")
            raise

    async def delete_notification_template(self, template_id: UUID) -> bool:
        """Delete a notification template."""
        try:
            self.supabase.table("notification_templates").delete().eq(
                "id", str(template_id)
            ).execute()
            return True
        except Exception as e:
            logger.error(f"Error deleting notification template: {e}")
            return False

    # Notification Sending

    async def _find_notification_log_by_idempotency_key(
        self, idempotency_key: str
    ) -> Optional[Dict[str, Any]]:
        """Find an existing delivery attempt for a stable notification key."""
        response = (
            self.supabase.table("notification_logs")
            .select("id, status, attempt_count")
            .eq("idempotency_key", idempotency_key)
            .limit(1)
            .execute()
        )
        rows = response.data if isinstance(response.data, list) else []
        return rows[0] if rows else None

    async def send_notification(
        self, request: SendNotificationRequest
    ) -> SendNotificationResponse:
        """Render, persist, and deliver one notification idempotently.

        A pending/failed log is retained and retried when the same
        ``idempotency_key`` is submitted again. Provider calls are delegated to
        an adapter so the notification workflow is independent of Resend.
        """
        try:
            # Get the notification event
            event = await self.get_notification_event_by_key(request.event_key)
            if not event:
                raise ValueError(f"Notification event not found: {request.event_key}")

            # Check if event is enabled
            if not event.is_enabled:
                logger.info(f"Notification event is disabled: {request.event_key}")
                return SendNotificationResponse(
                    success=False,
                    notification_log_id=UUID("0000000-0000-0000-0000-0000000"),
                    status=NotificationStatus.FAILED,
                    message="Notification event is disabled",
                )

            template_id = request.template_id or event.default_template_id
            template = None
            html_content = None
            text_content = None
            subject = ""

            if template_id:
                # Use custom template from database
                template = await self.get_notification_template(template_id)
                if template and template.is_active:
                    html_content = template.html_content
                    text_content = template.text_content
                    subject = template.subject
                    # Validate that all required variables for this template are present
                    template_required_vars = template.template_variables or []
                    validated_db_vars = validate_template_variables(
                        template_required_vars, request.template_variables
                    )

                    # Sanitize the validated variables for database templates
                    sanitized_db_vars = sanitize_template_variables(validated_db_vars)

                    # Replace variables in subject and content with sanitized validated values
                    for key, value in sanitized_db_vars.items():
                        html_content = html_content.replace(f"{{{key}}}", value)
                        if text_content:
                            text_content = text_content.replace(f"{{{key}}}", value)
                        subject = subject.replace(f"{{{key}}}", value)

            # Fallback to built-in template
            if not html_content and request.event_key in TEMPLATE_REGISTRY:
                # Validate built-in template variables with defaults applied
                validated_builtin_vars = validate_builtin_template_variables(
                    request.event_key, request.template_variables
                )

                # Sanitize the validated variables (with defaults applied) for built-in templates
                sanitized_builtin_vars = sanitize_template_variables(
                    validated_builtin_vars
                )

                # Use sanitized validated variables (with defaults applied) for built-in template
                template_data = TEMPLATE_REGISTRY[request.event_key]
                subject = template_data["subject"].format(**sanitized_builtin_vars)
                # Use sanitized validated variables (with defaults applied) for built-in template
                html_content = get_template_html(
                    request.event_key, sanitized_builtin_vars
                )

            if not html_content:
                raise ValueError(f"No template found for event: {request.event_key}")

            # Prepare sender details
            from_email = (
                template.from_email
                if template and template.from_email
                else self.from_email
            )
            from_name = (
                template.from_name
                if template and template.from_name
                else self.from_name
            )

            provider = NotificationProvider(self.email_provider.name)
            existing_log = None
            if request.idempotency_key:
                existing_log = await self._find_notification_log_by_idempotency_key(
                    request.idempotency_key
                )
                if (
                    existing_log
                    and existing_log.get("status") == NotificationStatus.SENT.value
                ):
                    return SendNotificationResponse(
                        success=True,
                        notification_log_id=UUID(str(existing_log["id"])),
                        status=NotificationStatus.SENT,
                        message="Notification was already sent",
                    )

            if existing_log:
                notification_log_id = UUID(str(existing_log["id"]))
            else:
                # Create notification log (pending) before the external call.
                log_data = NotificationLogCreate(
                    notification_event_id=event.id,
                    notification_template_id=template_id,
                    organization_id=request.organization_id,
                    user_id=request.user_id,
                    recipient_email=request.recipient_email,
                    recipient_name=request.recipient_name,
                    subject=subject,
                    status=NotificationStatus.PENDING,
                    provider=provider,
                    idempotency_key=request.idempotency_key,
                    metadata=request.template_variables,
                )

                log_response = (
                    self.supabase.table("notification_logs")
                    .insert(
                        {
                            "notification_event_id": str(
                                log_data.notification_event_id
                            ),
                            "notification_template_id": (
                                str(log_data.notification_template_id)
                                if log_data.notification_template_id
                                else None
                            ),
                            "organization_id": (
                                str(log_data.organization_id)
                                if log_data.organization_id
                                else None
                            ),
                            "user_id": (
                                str(log_data.user_id) if log_data.user_id else None
                            ),
                            "recipient_email": log_data.recipient_email,
                            "recipient_name": log_data.recipient_name,
                            "subject": log_data.subject,
                            "status": log_data.status.value,
                            "provider": log_data.provider.value,
                            "idempotency_key": log_data.idempotency_key,
                            "attempt_count": 0,
                            "metadata": log_data.metadata,
                        }
                    )
                    .execute()
                )

                if not log_response.data:
                    raise ValueError("Failed to create notification log")
                notification_log_id = UUID(log_response.data[0]["id"])

            attempt_count = int((existing_log or {}).get("attempt_count") or 0) + 1
            attempt_at = datetime.now(timezone.utc).isoformat()
            self.supabase.table("notification_logs").update(
                {
                    "status": NotificationStatus.PENDING.value,
                    "attempt_count": attempt_count,
                    "last_attempt_at": attempt_at,
                    "error_message": None,
                }
            ).eq("id", str(notification_log_id)).execute()

            try:
                email_response = await self.email_provider.send(
                    EmailMessage(
                        recipient_email=request.recipient_email,
                        recipient_name=request.recipient_name,
                        subject=subject,
                        html_content=html_content,
                        text_content=text_content,
                        from_email=from_email,
                        from_name=from_name,
                    )
                )

                # Update log with success
                self.supabase.table("notification_logs").update(
                    {
                        "status": NotificationStatus.SENT.value,
                        "provider": email_response.provider,
                        "provider_message_id": email_response.provider_message_id,
                        "sent_at": datetime.now(timezone.utc).isoformat(),
                    }
                ).eq("id", str(notification_log_id)).execute()

                logger.info(
                    f"Notification sent successfully: {request.event_key} to {request.recipient_email}"
                )

                return SendNotificationResponse(
                    success=True,
                    notification_log_id=notification_log_id,
                    status=NotificationStatus.SENT,
                    message="Notification sent successfully",
                )

            except Exception as send_error:
                # Update log with failure
                self.supabase.table("notification_logs").update(
                    {
                        "status": NotificationStatus.FAILED.value,
                        "error_message": str(send_error),
                    }
                ).eq("id", str(notification_log_id)).execute()

                logger.error(
                    "Error sending notification via %s: %s",
                    self.email_provider.name,
                    send_error,
                )

                return SendNotificationResponse(
                    success=False,
                    notification_log_id=notification_log_id,
                    status=NotificationStatus.FAILED,
                    message=f"Failed to send notification: {str(send_error)}",
                )

        except Exception as e:
            logger.error(f"Error in send_notification: {e}")
            raise

    async def retry_failed_notifications(
        self, limit: int = 100, now: Optional[datetime] = None
    ) -> NotificationRetryResult:
        """Retry eligible failed or interrupted deliveries.

        The retry pass only considers rows with an idempotency key. Older logs
        without a stable key are left untouched to avoid creating a duplicate
        delivery during a migration. A five-minute delay prevents a tight loop
        when a provider is unavailable.
        """
        now = now or datetime.now(timezone.utc)
        result = (
            self.supabase.table("notification_logs")
            .select("*, notification_events(event_key)")
            .in_(
                "status",
                [NotificationStatus.PENDING.value, NotificationStatus.FAILED.value],
            )
            .order("created_at")
            .limit(limit)
            .execute()
        )
        summary = NotificationRetryResult()

        for row in result.data or []:
            key = row.get("idempotency_key")
            if not key:
                summary.skipped += 1
                continue

            last_attempt = row.get("last_attempt_at")
            if last_attempt:
                parsed = (
                    last_attempt
                    if isinstance(last_attempt, datetime)
                    else datetime.fromisoformat(
                        str(last_attempt).replace("Z", "+00:00")
                    )
                )
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                if parsed + timedelta(minutes=RETRY_DELAY_MINUTES) > now:
                    summary.skipped += 1
                    continue

            event_data = row.get("notification_events") or {}
            if isinstance(event_data, list):
                event_data = event_data[0] if event_data else {}
            event_key = event_data.get("event_key")
            if not event_key:
                summary.failed += 1
                continue

            try:
                response = await self.send_notification(
                    SendNotificationRequest(
                        event_key=event_key,
                        recipient_email=row["recipient_email"],
                        recipient_name=row.get("recipient_name"),
                        organization_id=(
                            UUID(str(row["organization_id"]))
                            if row.get("organization_id")
                            else None
                        ),
                        user_id=(
                            UUID(str(row["user_id"])) if row.get("user_id") else None
                        ),
                        template_variables=row.get("metadata") or {},
                        template_id=(
                            UUID(str(row["notification_template_id"]))
                            if row.get("notification_template_id")
                            else None
                        ),
                        idempotency_key=key,
                    )
                )
                summary.processed += 1
                if response.success:
                    summary.succeeded += 1
                else:
                    summary.failed += 1
            except Exception:
                summary.processed += 1
                summary.failed += 1
                logger.exception("Notification retry failed for log %s", row.get("id"))

        return summary

    # Notification Logs

    async def get_notification_logs(
        self,
        organization_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
        status: Optional[NotificationStatus] = None,
        limit: int = 100,
    ) -> List[NotificationLog]:
        """Get notification logs with optional filters."""
        try:
            query = self.supabase.table("notification_logs").select("*")

            if organization_id:
                query = query.eq("organization_id", str(organization_id))
            if user_id:
                query = query.eq("user_id", str(user_id))
            if status:
                query = query.eq("status", status.value)

            response = query.order("created_at", desc=True).limit(limit).execute()
            return [NotificationLog(**item) for item in response.data]
        except Exception as e:
            logger.error(f"Error fetching notification logs: {e}")
            return []

    async def get_notification_stats(
        self, organization_id: Optional[UUID] = None
    ) -> NotificationStats:
        """Get notification statistics."""
        try:
            query = self.supabase.table("notification_logs").select("*")
            if organization_id:
                query = query.eq("organization_id", str(organization_id))

            response = query.execute()
            logs = [NotificationLog(**item) for item in response.data]

            total_sent = sum(1 for log in logs if log.status == NotificationStatus.SENT)
            total_failed = sum(
                1 for log in logs if log.status == NotificationStatus.FAILED
            )
            total_pending = sum(
                1 for log in logs if log.status == NotificationStatus.PENDING
            )

            # Group by event
            by_event: Dict[str, int] = {}
            for log in logs:
                event_id = str(log.notification_event_id)
                by_event[event_id] = by_event.get(event_id, 0) + 1

            # Group by status
            by_status = {
                "sent": total_sent,
                "failed": total_failed,
                "pending": total_pending,
            }

            # Recent failures
            recent_failures = [
                log for log in logs if log.status == NotificationStatus.FAILED
            ][:10]

            return NotificationStats(
                total_sent=total_sent,
                total_failed=total_failed,
                total_pending=total_pending,
                by_event=by_event,
                by_status=by_status,
                recent_failures=recent_failures,
            )
        except Exception as e:
            logger.error(f"Error getting notification stats: {e}")
            return NotificationStats(
                total_sent=0,
                total_failed=0,
                total_pending=0,
                by_event={},
                by_status={},
                recent_failures=[],
            )


# Global service instance
notification_service = NotificationService()
