"""Google Sheets service for confirmed voice-captured service inquiries."""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any, Optional
from urllib.parse import quote
from uuid import uuid4

import httpx

logger = logging.getLogger(__name__)

_API_BASE = "https://sheets.googleapis.com/v4"
_TIMEOUT = 20.0
_EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
_SPREADSHEET_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{10,}$")
_DEFAULT_APPEND_RANGE = "Lead submissions!A:L"
_DEFAULT_DEDUPE_RANGE = "Lead submissions!A:A"


def _default_client_factory() -> httpx.AsyncClient:
    """Create the production Google Sheets HTTP client."""
    return httpx.AsyncClient(timeout=_TIMEOUT)


class GoogleSheetsLeadService:
    """Append one confirmed service inquiry to a configured Google Sheet.

    The service deliberately exposes a small, business-level contract instead
    of making the voice model construct arbitrary spreadsheet ranges or rows.
    It performs a read-before-append using the session submission id so a
    retry after an uncertain network response can discover an already-written
    row. The mutation itself is never automatically retried because Google
    Sheets append has no provider-side idempotency key.
    """

    def __init__(
        self,
        *,
        access_token: str,
        spreadsheet_id: str,
        append_range: str = _DEFAULT_APPEND_RANGE,
        dedupe_range: str = _DEFAULT_DEDUPE_RANGE,
        lead_source: str = "Voice inquiry",
        client_factory: Optional[Callable[[], httpx.AsyncClient]] = None,
    ) -> None:
        self.access_token = access_token.strip()
        self.spreadsheet_id = self.extract_spreadsheet_id(spreadsheet_id)
        self.append_range = append_range.strip() or _DEFAULT_APPEND_RANGE
        self.dedupe_range = dedupe_range.strip() or _DEFAULT_DEDUPE_RANGE
        self.lead_source = lead_source.strip()[:120] or "Voice inquiry"
        self.client_factory = client_factory or _default_client_factory

    @staticmethod
    def extract_spreadsheet_id(value: str) -> str:
        """Normalize a Google Sheets URL or id to the provider resource id."""
        candidate = str(value or "").strip()
        marker = "/spreadsheets/d/"
        if marker in candidate:
            candidate = candidate.split(marker, 1)[1].split("/", 1)[0]
            candidate = candidate.split("?", 1)[0].split("#", 1)[0]
        return candidate

    async def capture_lead(
        self,
        *,
        caller_name: str,
        caller_email: str = "",
        caller_phone: str = "",
        service_needed: str,
        issue_summary: str,
        property_address: str = "",
        urgency: str = "",
        preferred_callback_window: str = "",
        submission_id: str = "",
        captured_at: Optional[datetime] = None,
    ) -> dict[str, Any]:
        """Validate and append a complete service inquiry as one sheet row.

        Args:
            caller_name: Person requesting service.
            caller_email: Optional email follow-up channel.
            caller_phone: Optional phone follow-up channel.
            service_needed: Requested service category.
            issue_summary: Concise caller-provided description of the issue.
            property_address: Service location when provided.
            urgency: Caller-stated urgency, not a technician assessment.
            preferred_callback_window: Requested follow-up window.
            submission_id: Stable session-scoped id used for deduplication.
            captured_at: Optional clock seam for deterministic tests.

        Returns:
            A stable result with ``status`` of ``created``, ``needs_details``,
            or ``error``. Provider response bodies are never returned.
        """
        validation = self._validate(
            caller_name=caller_name,
            caller_email=caller_email,
            caller_phone=caller_phone,
            service_needed=service_needed,
            issue_summary=issue_summary,
            property_address=property_address,
            urgency=urgency,
            preferred_callback_window=preferred_callback_window,
        )
        if validation:
            return validation

        submission_id = submission_id.strip() or str(uuid4())
        configuration_error = self._validate_configuration()
        if configuration_error:
            return configuration_error

        existing = await self._find_submission(submission_id)
        if isinstance(existing, dict) and existing.get("status") == "error":
            return existing
        if existing:
            return self._created_result(
                caller_name=caller_name,
                caller_email=caller_email,
                submission_id=submission_id,
                updated_range=existing.get("updated_range"),
                deduplicated=True,
            )

        timestamp = captured_at or datetime.now(timezone.utc)
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        timestamp = timestamp.astimezone(timezone.utc)
        values = [
            submission_id,
            timestamp.isoformat(timespec="seconds").replace("+00:00", "Z"),
            self.lead_source,
            caller_name.strip(),
            caller_email.strip().lower(),
            caller_phone.strip(),
            service_needed.strip(),
            issue_summary.strip(),
            property_address.strip(),
            urgency.strip(),
            preferred_callback_window.strip(),
            "New",
        ]
        status, body = await self._append_row(values)
        if status != 200:
            return self._provider_error(status)

        updates = body.get("updates") if isinstance(body, dict) else {}
        updated_range = (
            str(updates.get("updatedRange"))
            if isinstance(updates, dict) and updates.get("updatedRange")
            else None
        )
        return self._created_result(
            caller_name=caller_name,
            caller_email=caller_email,
            submission_id=submission_id,
            updated_range=updated_range,
            deduplicated=False,
        )

    async def _find_submission(self, submission_id: str) -> Optional[dict[str, Any]]:
        """Find an existing session row without returning sheet contents."""
        status, body = await self._request(
            "GET",
            f"/spreadsheets/{self.spreadsheet_id}/values/{self._encoded_range(self.dedupe_range)}",
        )
        if status != 200:
            return self._provider_error(status)
        values = body.get("values") if isinstance(body, dict) else []
        if not isinstance(values, list):
            return None
        for row_index, row in enumerate(values, start=1):
            if not isinstance(row, list) or not row:
                continue
            if str(row[0]).strip() == submission_id:
                return {
                    "record_id": submission_id,
                    "updated_range": f"{self.dedupe_range.split('!', 1)[0]}!A{row_index}",
                }
        return None

    async def _append_row(self, values: list[str]) -> tuple[int, dict[str, Any]]:
        """Append exactly once and return a sanitized provider response."""
        return await self._request(
            "POST",
            f"/spreadsheets/{self.spreadsheet_id}/values/{self._encoded_range(self.append_range)}:append",
            params={
                "valueInputOption": "RAW",
                "insertDataOption": "INSERT_ROWS",
            },
            json_body={"values": [values]},
        )

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[dict[str, Any]] = None,
        json_body: Optional[dict[str, Any]] = None,
    ) -> tuple[int, dict[str, Any]]:
        """Make one bounded authenticated request without exposing PII."""
        if not self.access_token:
            return 401, {}
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        client: Optional[httpx.AsyncClient] = None
        try:
            client = self.client_factory()
            response = await client.request(
                method,
                f"{_API_BASE}{path}",
                params=params,
                json=json_body,
                headers=headers,
            )
            try:
                body = response.json() if response.content else {}
            except ValueError:
                body = {}
            return response.status_code, body if isinstance(body, dict) else {}
        except httpx.HTTPError as exc:
            logger.warning(
                "Google Sheets lead request failed method=%s path=%s error=%s",
                method,
                path,
                type(exc).__name__,
            )
            return 0, {}
        except Exception as exc:  # noqa: BLE001 - provider boundary must be safe
            logger.warning(
                "Google Sheets lead request failed method=%s path=%s error=%s",
                method,
                path,
                type(exc).__name__,
            )
            return 0, {}
        finally:
            if client is not None:
                await client.aclose()

    def _validate_configuration(self) -> Optional[dict[str, Any]]:
        """Validate provider configuration before any Google request."""
        if not self.access_token:
            return self._error(
                "authentication_required",
                "Google Sheets is not connected for this demo.",
                next_action="reauthorize",
                retryable=False,
            )
        if not _SPREADSHEET_ID_PATTERN.fullmatch(self.spreadsheet_id):
            return self._error(
                "invalid_configuration",
                "The Google Sheets destination is not configured for this demo.",
                next_action="configure_tool",
                retryable=False,
            )
        if not self._valid_range(self.append_range) or not self._valid_range(
            self.dedupe_range
        ):
            return self._error(
                "invalid_configuration",
                "The Google Sheets ranges are not configured correctly.",
                next_action="configure_tool",
                retryable=False,
            )
        return None

    @staticmethod
    def _valid_range(value: str) -> bool:
        """Reject empty or newline-bearing A1 ranges before URL construction."""
        return bool(value and len(value) <= 200 and "\n" not in value and "!" in value)

    @staticmethod
    def _validate(
        *,
        caller_name: str,
        caller_email: str,
        caller_phone: str,
        service_needed: str,
        issue_summary: str,
        property_address: str,
        urgency: str,
        preferred_callback_window: str,
    ) -> Optional[dict[str, Any]]:
        """Validate the minimum follow-up details before provider I/O."""
        required = (
            ("caller_name", caller_name, "Ask for the caller's name."),
            ("service_needed", service_needed, "Ask what service is needed."),
            (
                "issue_summary",
                issue_summary,
                "Ask for a short description of the issue.",
            ),
        )
        for field, value, message in required:
            if not value.strip():
                return GoogleSheetsLeadService._input_error(field, message)
        if not caller_email.strip() and not caller_phone.strip():
            return GoogleSheetsLeadService._input_error(
                "caller_email",
                "Ask for an email address or phone number so the inquiry can be followed up.",
            )
        if caller_email.strip() and not _EMAIL_PATTERN.fullmatch(caller_email.strip()):
            return GoogleSheetsLeadService._input_error(
                "caller_email", "Ask for a valid email address."
            )
        max_lengths = {
            "caller_name": (caller_name, 200),
            "caller_email": (caller_email, 320),
            "caller_phone": (caller_phone, 80),
            "service_needed": (service_needed, 300),
            "issue_summary": (issue_summary, 1000),
            "property_address": (property_address, 500),
            "urgency": (urgency, 200),
            "preferred_callback_window": (preferred_callback_window, 200),
        }
        for field, (value, limit) in max_lengths.items():
            if len(value.strip()) > limit:
                return GoogleSheetsLeadService._input_error(
                    field,
                    f"Keep {field.replace('_', ' ')} to {limit} characters or fewer.",
                )
        return None

    @staticmethod
    def _input_error(field: str, message: str) -> dict[str, Any]:
        """Build a model-actionable validation result."""
        return {
            "status": "needs_details",
            "provider": "google_sheets",
            "message": message,
            "next_action": "ask_for_missing_detail",
            "error": {
                "code": "missing_or_invalid_detail",
                "field": field,
                "message": message,
                "next_action": "ask_for_missing_detail",
                "retryable": True,
            },
        }

    def _created_result(
        self,
        *,
        caller_name: str,
        caller_email: str,
        submission_id: str,
        updated_range: Optional[str],
        deduplicated: bool,
    ) -> dict[str, Any]:
        """Return the stable success contract used by the voice model and receipt."""
        return {
            "status": "created",
            "provider": "google_sheets",
            "message": (
                "Service inquiry was already present in Google Sheets."
                if deduplicated
                else "Service inquiry captured in Google Sheets."
            ),
            "sheet": {
                "provider": "google_sheets",
                "record_type": "lead_row",
                "record_id": submission_id,
                "updated_range": updated_range,
            },
            "lead": {
                "id": submission_id,
                "name": caller_name.strip(),
                "email": caller_email.strip().lower() or None,
            },
            "deduplicated": deduplicated,
        }

    @classmethod
    def _provider_error(cls, status_code: int) -> dict[str, Any]:
        """Map Google status codes to safe, actionable tool errors."""
        if status_code in (401, 403):
            return cls._error(
                "authentication_required",
                "Google Sheets authorization is unavailable for this demo.",
                next_action="reauthorize",
                retryable=False,
            )
        if status_code == 404:
            return cls._error(
                "not_found",
                "The configured Google Sheet could not be found.",
                next_action="configure_tool",
                retryable=False,
            )
        if status_code == 429 or status_code >= 500 or status_code == 0:
            return cls._error(
                "temporary_failure",
                "Google Sheets is temporarily unavailable. Please try again.",
                next_action="retry_later",
                retryable=True,
            )
        return cls._error(
            "provider_rejected",
            "Google Sheets could not save the service inquiry.",
            next_action="verify_configuration",
            retryable=False,
        )

    @staticmethod
    def _error(
        code: str,
        message: str,
        *,
        next_action: str,
        retryable: bool,
    ) -> dict[str, Any]:
        """Build one stable error shape without provider response details."""
        return {
            "status": "error",
            "provider": "google_sheets",
            "message": message,
            "next_action": next_action,
            "error": {
                "code": code,
                "message": message,
                "next_action": next_action,
                "retryable": retryable,
            },
        }

    @staticmethod
    def _encoded_range(value: str) -> str:
        """Encode an A1 range while retaining Google range punctuation."""
        return quote(value, safe="!:$'()")


__all__ = ["GoogleSheetsLeadService"]
