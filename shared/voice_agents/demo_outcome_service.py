"""Visitor-safe outcome receipts for public demo voice sessions.

Demo receipts are deliberately narrower than observability.  A receipt stores
only the confirmed fields and provider summary for a side-effecting demo
workflow, keyed by the opaque voice session id.  It is never a general tool
trace and it is never queried without a short-lived signed receipt token.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from urllib.parse import urlsplit

import jwt

from shared.config import supabase_config
from shared.config.settings import settings
from shared.voice_agents.tools.base.tool_context import ToolContext

logger = logging.getLogger(__name__)

DEMO_OUTCOME_TOKEN_TYPE = "demo_outcome"
DEMO_OUTCOME_TOKEN_TTL = timedelta(hours=24)
DEMO_OUTCOME_RETENTION = timedelta(days=7)
_SUCCESS_STATUSES = {
    "accepted",
    "created",
    "sent",
    "succeeded",
    "updated",
    "cancelled",
}
_PENDING_STATUSES = {"confirmation_required", "pending", "needs_details"}
_EMAIL_FUNCTION_PROVIDERS = {
    "send_email": "gmail",
    "send_email_reply": "gmail",
    "send_resend_email": "resend",
}


@dataclass(frozen=True)
class DemoOutcomeTokenClaims:
    """Verified claims that authorize one visitor's demo receipt."""

    session_id: str
    agent_id: str
    demo_slug: str


def _jwt_secret(secret: Optional[str] = None) -> str:
    """Resolve the shared signing secret without introducing a fallback secret."""
    return (secret or settings.jwt_secret_key or "").strip()


def create_demo_outcome_token(
    *,
    session_id: str,
    agent_id: str,
    demo_slug: str,
    secret: Optional[str] = None,
    expires_in: timedelta = DEMO_OUTCOME_TOKEN_TTL,
) -> str:
    """Create a signed token for the outcome of one demo call.

    Args:
        session_id: Voice session whose receipt may be read.
        agent_id: Agent id bound to the session.
        demo_slug: Public slug bound to the session.
        secret: Optional test signing secret; production uses the shared JWT
            setting.
        expires_in: Token lifetime.

    Returns:
        An HS256 JWT accepted by :func:`verify_demo_outcome_token`.

    Raises:
        ValueError: If a required claim or signing secret is missing.
    """
    values = (session_id.strip(), agent_id.strip(), demo_slug.strip().lower())
    if not all(values):
        raise ValueError("Demo outcome token claims must be non-empty")
    signing_secret = _jwt_secret(secret)
    if not signing_secret:
        raise ValueError("JWT secret is not configured for demo outcomes")
    if expires_in <= timedelta(0):
        raise ValueError("Demo outcome token lifetime must be positive")

    now = datetime.now(timezone.utc)
    payload = {
        "type": DEMO_OUTCOME_TOKEN_TYPE,
        "session_id": values[0],
        "agent_id": values[1],
        "demo_slug": values[2],
        "iat": now,
        "exp": now + expires_in,
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, signing_secret, algorithm="HS256")


def verify_demo_outcome_token(
    token: str, *, secret: Optional[str] = None
) -> Optional[DemoOutcomeTokenClaims]:
    """Verify a receipt token and return its bound claims, or ``None``."""
    signing_secret = _jwt_secret(secret)
    if not signing_secret or not token.strip():
        return None
    try:
        payload = jwt.decode(token, signing_secret, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None

    if payload.get("type") != DEMO_OUTCOME_TOKEN_TYPE:
        return None
    session_id = payload.get("session_id")
    agent_id = payload.get("agent_id")
    demo_slug = payload.get("demo_slug")
    if not all(
        isinstance(value, str) and value.strip()
        for value in (session_id, agent_id, demo_slug)
    ):
        return None
    return DemoOutcomeTokenClaims(
        session_id=session_id.strip(),
        agent_id=agent_id.strip(),
        demo_slug=demo_slug.strip().lower(),
    )


def _response_rows(response: Any) -> list[dict[str, Any]]:
    """Extract rows from a Supabase response without depending on its class."""
    data = getattr(response, "data", None)
    if data is None and isinstance(response, dict):
        data = response.get("data")
    return [row for row in (data or []) if isinstance(row, dict)]


def _json_safe(value: Any) -> Any:
    """Convert common provider values into JSON-safe receipt data."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return str(value)


def _text(value: Any, *, limit: int = 1000) -> str:
    """Return bounded text for a visitor receipt."""
    return str(value or "").strip()[:limit]


def _safe_provider_url(provider: str, value: Any) -> Optional[str]:
    """Allow only provider-generated links that are safe for a visitor.

    Demo receipts never trust a URL supplied as a model argument. At present
    Google Calendar is the only provider with a useful, provider-generated
    record link. Google Sheets deliberately has no visitor link because a
    spreadsheet URL exposes the shared demo sheet and other visitors' rows.
    """
    raw = _text(value, limit=2048)
    if not raw or provider != "google_calendar":
        return None
    try:
        parsed = urlsplit(raw)
        port = parsed.port
    except ValueError:
        return None
    hostname = (parsed.hostname or "").lower()
    if (
        parsed.scheme != "https"
        or not hostname
        or parsed.username
        or parsed.password
        or parsed.fragment
        or port is not None
    ):
        return None
    if hostname == "www.google.com":
        allowed_path = parsed.path.startswith("/calendar/event")
    elif hostname == "calendar.google.com":
        allowed_path = parsed.path.startswith("/calendar/")
    else:
        allowed_path = False
    return raw if allowed_path else None


def _status_for_result(result: Any) -> str:
    """Map a provider/tool response into the receipt status vocabulary."""
    if not isinstance(result, dict):
        return "failed"
    raw_status = _text(result.get("status"), limit=64).lower()
    if raw_status in _SUCCESS_STATUSES:
        return "succeeded"
    if raw_status in _PENDING_STATUSES:
        return "pending"
    if raw_status in {"not_configured", "error", "failed", "busy"}:
        return "failed"
    if isinstance(result.get("error"), dict) or result.get("error"):
        return "failed"
    return "pending"


def _error_code(result: Any) -> Optional[str]:
    """Extract a non-sensitive provider error code for the receipt."""
    if not isinstance(result, dict):
        return "invalid_tool_result"
    error = result.get("error")
    if isinstance(error, dict):
        code = _text(error.get("code"), limit=80)
        if code:
            return code
    code = _text(result.get("code"), limit=80)
    return code or None


def _lead_payload(
    arguments: dict[str, Any], result: Any
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build the allowlisted lead fields and provider summary."""
    field_names = (
        "caller_name",
        "caller_email",
        "caller_phone",
        "service_needed",
        "issue_summary",
        "property_address",
        "urgency",
        "preferred_callback_window",
    )
    fields = {
        name: _text(arguments.get(name), limit=1000)
        for name in field_names
        if _text(arguments.get(name), limit=1000)
    }
    result_dict = result if isinstance(result, dict) else {}
    lead = result_dict.get("lead") if isinstance(result_dict.get("lead"), dict) else {}
    crm = result_dict.get("crm") if isinstance(result_dict.get("crm"), dict) else {}
    sheet = (
        result_dict.get("sheet") if isinstance(result_dict.get("sheet"), dict) else {}
    )
    provider = _text(
        result_dict.get("provider") or crm.get("provider") or "hubspot", limit=64
    )
    record = sheet if provider == "google_sheets" else crm
    summary = {
        "record_type": _text(
            record.get("record_type")
            or ("lead_row" if provider == "google_sheets" else "contact"),
            limit=64,
        )
        or None,
        "record_id": _text(record.get("record_id") or lead.get("id"), limit=120)
        or None,
        "record_status": _text(result_dict.get("status"), limit=64) or None,
        "note_id": _text(
            (
                (result_dict.get("note") or {}).get("id")
                if isinstance(result_dict.get("note"), dict)
                else ""
            ),
            limit=120,
        )
        or None,
        "updated_range": _text(record.get("updated_range"), limit=200) or None,
        "deduplicated": (
            result_dict.get("deduplicated")
            if isinstance(result_dict.get("deduplicated"), bool)
            else None
        ),
        "message": _text(result_dict.get("message"), limit=500) or None,
    }
    record_url = _safe_provider_url(
        provider, record.get("record_url") or result_dict.get("record_url")
    )
    if record_url:
        summary["record_url"] = record_url
    return fields, summary


_PUBLIC_SHEET_FIELDS = {
    "caller name",
    "caller email",
    "caller phone",
    "service needed",
    "issue summary",
    "service address",
    "urgency",
    "preferred callback window",
    "customer name",
    "customer email",
    "customer phone",
    "item",
    "items",
    "quantity",
    "order details",
    "order notes",
    "pickup notes",
    "notes",
}


def _sheet_row_payload(
    arguments: dict[str, Any], result: Any
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build a bounded public receipt for a generic Sheets row mutation.

    The generic tool accepts arbitrary header names, but a public demo receipt
    must not mirror arbitrary sheet cells back to an unauthenticated visitor.
    Only the business fields used by the shipped demos are allowlisted here;
    the provider summary contains identifiers and status only.
    """
    values = arguments.get("values")
    fields: dict[str, Any] = {}
    if isinstance(values, dict):
        for key, value in values.items():
            normalized_key = " ".join(str(key).strip().split()).casefold()
            if normalized_key not in _PUBLIC_SHEET_FIELDS:
                continue
            if isinstance(value, (dict, list, tuple, set)):
                continue
            text_value = _text(value, limit=1000)
            if text_value:
                fields[str(key).strip()] = text_value

    result_dict = result if isinstance(result, dict) else {}
    sheet = (
        result_dict.get("sheet") if isinstance(result_dict.get("sheet"), dict) else {}
    )
    summary = {
        "record_type": _text(sheet.get("record_type") or "row", limit=64) or "row",
        "record_label": _text(sheet.get("record_label"), limit=80) or None,
        "record_id": _text(sheet.get("record_id"), limit=120) or None,
        "record_status": _text(result_dict.get("status"), limit=64) or None,
        "updated_range": _text(sheet.get("updated_range"), limit=200) or None,
        "deduplicated": (
            result_dict.get("deduplicated")
            if isinstance(result_dict.get("deduplicated"), bool)
            else None
        ),
        "message": _text(result_dict.get("message"), limit=500) or None,
    }
    return fields, summary


def _appointment_payload(
    arguments: dict[str, Any], result: Any
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build the allowlisted appointment fields and calendar summary."""
    field_names = (
        "caller_name",
        "caller_email",
        "caller_phone",
        "purpose",
        "start_time",
        "duration_minutes",
        "notes",
    )
    fields: dict[str, Any] = {}
    for name in field_names:
        value = arguments.get(name)
        if name == "duration_minutes":
            if isinstance(value, int) and not isinstance(value, bool):
                fields[name] = value
            continue
        text_value = _text(value, limit=1000)
        if text_value:
            fields[name] = text_value

    result_dict = result if isinstance(result, dict) else {}
    appointment = (
        result_dict.get("appointment")
        if isinstance(result_dict.get("appointment"), dict)
        else {}
    )
    summary = {
        "record_type": "calendar_event",
        "record_id": _text(appointment.get("id"), limit=120) or None,
        "record_status": _text(result_dict.get("status"), limit=64) or None,
        "start_time": _text(appointment.get("start_time"), limit=80) or None,
        "end_time": _text(appointment.get("end_time"), limit=80) or None,
        "message": _text(result_dict.get("message"), limit=500) or None,
    }
    record_url = _safe_provider_url(
        "google_calendar",
        appointment.get("record_url") or result_dict.get("record_url"),
    )
    if record_url:
        summary["record_url"] = record_url
    return fields, summary


def _email_status(result: Any) -> str:
    """Map an independent email tool result without assuming one provider shape."""
    if not isinstance(result, dict):
        return "failed"
    raw_status = _text(result.get("status"), limit=64).lower()
    if raw_status in {"accepted", "sent", "succeeded"}:
        return "succeeded"
    if raw_status in {
        "error",
        "failed",
        "not_configured",
        "partial",
        "rejected",
        "unavailable",
    } or result.get("error"):
        return "failed"
    # Gmail returns the sent message id rather than a status field.
    if _text(result.get("id"), limit=120):
        return "succeeded"
    return "pending"


def _email_payload(
    *, provider: str, result: Any
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build a PII-free receipt summary for an independent email action."""
    result_dict = result if isinstance(result, dict) else {}
    email_status = _email_status(result)
    provider_status = _text(result_dict.get("status"), limit=64) or None
    provider_message_ids = result_dict.get("provider_message_ids")
    first_provider_message_id = (
        provider_message_ids[0]
        if isinstance(provider_message_ids, list) and provider_message_ids
        else None
    )
    record_id = (
        _text(result_dict.get("id") or first_provider_message_id, limit=120) or None
    )
    if provider == "gmail":
        message = (
            "Gmail confirmed the email was sent."
            if email_status == "succeeded"
            else "Gmail did not confirm the email was sent."
        )
    else:
        message = (
            "Resend accepted the email for the configured route."
            if email_status == "succeeded"
            else "Resend did not confirm acceptance of the email."
        )
    return {}, {
        "record_type": "email",
        "record_id": record_id,
        "record_status": provider_status,
        "message": message,
    }


def build_demo_outcome_payload(
    *, function_name: str, arguments: dict[str, Any], result: Any
) -> Optional[dict[str, Any]]:
    """Return an allowlisted receipt payload for a side-effecting demo call.

    The function names are the only native actions that are visitor-visible.
    Availability searches, generic tools, and arbitrary future tool arguments
    are intentionally not recorded.
    """
    email_provider = _EMAIL_FUNCTION_PROVIDERS.get(function_name)
    if email_provider:
        action_type = "email_delivery"
        provider = email_provider
        fields, summary = _email_payload(provider=provider, result=result)
        status = _email_status(result)
        error_code = _error_code(result) if status != "succeeded" else None
    elif function_name == "capture_lead":
        action_type = "lead_capture"
        result_dict = result if isinstance(result, dict) else {}
        provider = _text(
            result_dict.get("provider")
            or (
                result_dict.get("crm", {}).get("provider")
                if isinstance(result_dict.get("crm"), dict)
                else ""
            )
            or "hubspot",
            limit=64,
        )
        if provider not in {"hubspot", "google_sheets"}:
            provider = "hubspot"
        fields, summary = _lead_payload(arguments, result)
        status = _status_for_result(result)
        error_code = _error_code(result)
    elif function_name == "create_row":
        action_type = "sheet_row_created"
        provider = "google_sheets"
        fields, summary = _sheet_row_payload(arguments, result)
        status = _status_for_result(result)
        error_code = _error_code(result)
    elif function_name == "create_appointment":
        action_type = "appointment_booking"
        provider = "google_calendar"
        fields, summary = _appointment_payload(arguments, result)
        status = _status_for_result(result)
        error_code = _error_code(result)
    else:
        return None
    return {
        "action_type": action_type,
        "provider": provider,
        "status": status,
        "error_code": error_code,
        "captured_fields": _json_safe(fields),
        "provider_result": _json_safe(summary),
    }


class DemoOutcomeService:
    """Persist and read short-lived demo action receipts."""

    def __init__(self, client: Any = None) -> None:
        self.client = client

    def _client(self) -> Any:
        """Resolve the service-role client at call time for testability."""
        return self.client or supabase_config.service_client

    def _record_sync(self, *, context: ToolContext, payload: dict[str, Any]) -> bool:
        client = self._client()
        if client is None:
            return False
        row = {
            "session_id": context.session_id,
            "agent_id": context.agent_id,
            "organization_id": context.organization_id,
            "demo_slug": context.demo_slug,
            "action_type": payload["action_type"],
            "provider": payload["provider"],
            "status": payload["status"],
            "error_code": payload.get("error_code"),
            "captured_fields": payload["captured_fields"],
            "provider_result": payload["provider_result"],
            "expires_at": (
                datetime.now(timezone.utc) + DEMO_OUTCOME_RETENTION
            ).isoformat(),
        }
        response = client.table("demo_outcome_receipts").insert(row).execute()
        return bool(_response_rows(response))

    async def record(
        self, *, context: Optional[ToolContext], payload: dict[str, Any]
    ) -> bool:
        """Record one demo action without delaying the voice event loop."""
        if not context or not context.is_demo:
            return False
        if not context.session_id or not context.agent_id or not context.demo_slug:
            return False
        try:
            return await asyncio.to_thread(
                self._record_sync, context=context, payload=payload
            )
        except Exception:
            # A receipt outage must never turn a successful provider mutation
            # into a failed voice call. The provider result remains authoritative.
            logger.exception("Could not persist demo outcome receipt")
            return False

    def _list_sync(
        self, *, session_id: str, agent_id: str, demo_slug: str
    ) -> list[dict[str, Any]]:
        client = self._client()
        if client is None:
            raise RuntimeError("Demo outcome storage is not configured")
        response = (
            client.table("demo_outcome_receipts")
            .select(
                "id,action_type,provider,status,error_code,captured_fields,"
                "provider_result,created_at,expires_at"
            )
            .eq("session_id", session_id)
            .eq("agent_id", agent_id)
            .eq("demo_slug", demo_slug)
            .gt("expires_at", datetime.now(timezone.utc).isoformat())
            .order("created_at")
            .limit(20)
            .execute()
        )
        return _response_rows(response)

    async def list_for_session(
        self, *, session_id: str, agent_id: str, demo_slug: str
    ) -> list[dict[str, Any]]:
        """Return non-expired receipts for one verified demo session."""
        return await asyncio.to_thread(
            self._list_sync,
            session_id=session_id,
            agent_id=agent_id,
            demo_slug=demo_slug,
        )


demo_outcome_service = DemoOutcomeService()


async def record_demo_tool_outcome(
    *,
    context: Optional[ToolContext],
    function_name: str,
    arguments: dict[str, Any],
    result: Any,
) -> bool:
    """Record a known demo mutation using the visitor receipt allowlist."""
    if not context or not context.is_demo:
        return False
    payload = build_demo_outcome_payload(
        function_name=function_name,
        arguments=arguments,
        result=result,
    )
    if payload is None:
        return False
    return await demo_outcome_service.record(context=context, payload=payload)


__all__ = [
    "DEMO_OUTCOME_TOKEN_TTL",
    "DemoOutcomeService",
    "DemoOutcomeTokenClaims",
    "build_demo_outcome_payload",
    "create_demo_outcome_token",
    "demo_outcome_service",
    "record_demo_tool_outcome",
    "verify_demo_outcome_token",
]
