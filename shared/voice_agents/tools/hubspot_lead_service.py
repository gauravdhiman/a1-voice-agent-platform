"""HubSpot contact-and-note service for voice-captured service inquiries."""

from __future__ import annotations

import re
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

_TIMEOUT = 20.0
_EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def _default_client_factory() -> httpx.AsyncClient:
    """Create the production HubSpot HTTP client."""
    return httpx.AsyncClient(timeout=_TIMEOUT)


class HubSpotLeadService:
    """Create or update a HubSpot contact and attach the full inquiry note.

    HubSpot's formal Leads object is not available in every subscription. The
    broadly available CRM contract is a contact plus a note associated to that
    contact, which keeps the demo useful on a free CRM account and preserves
    the complete service context for the business owner.
    """

    def __init__(
        self,
        *,
        access_token: str,
        base_url: str = "https://api.hubapi.com",
        lead_source: str = "Voice inquiry",
        client_factory: Optional[Callable[[], httpx.AsyncClient]] = None,
    ) -> None:
        self.access_token = access_token.strip()
        self.base_url = base_url.rstrip("/") or "https://api.hubapi.com"
        self.lead_source = lead_source.strip()[:120] or "Voice inquiry"
        self.client_factory = client_factory or _default_client_factory

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
    ) -> dict[str, Any]:
        """Upsert one contact and add a note with the service inquiry.

        Email is preferred as the stable contact key; phone is accepted as a
        fallback for callers who decline to provide email. At least one is
        required so a retry cannot silently create an unaddressable duplicate.
        """
        validation = self._validate(
            caller_name=caller_name,
            caller_email=caller_email,
            caller_phone=caller_phone,
            service_needed=service_needed,
            issue_summary=issue_summary,
        )
        if validation:
            return validation

        email = caller_email.strip().lower()
        phone = caller_phone.strip()
        properties = self._contact_properties(
            caller_name=caller_name,
            caller_email=email,
            caller_phone=phone,
            property_address=property_address,
        )
        lookup_property = "email" if email else "phone"
        lookup_value = email or phone
        existing = await self._find_contact(lookup_property, lookup_value)
        if isinstance(existing, dict) and existing.get("status") == "error":
            return existing

        contact_id = existing.get("id") if isinstance(existing, dict) else None
        if contact_id:
            status, body = await self._request(
                "PATCH",
                f"/crm/v3/objects/contacts/{contact_id}",
                json_body={"properties": properties},
            )
            if status not in (200, 201):
                return self._provider_error(status)
            contact_status = "updated"
        else:
            status, body = await self._request(
                "POST", "/crm/v3/objects/contacts", json_body={"properties": properties}
            )
            if status == 409:
                # A concurrent retry may have created the contact between the
                # search and insert. Resolve it once, then patch the same row.
                existing = await self._find_contact(lookup_property, lookup_value)
                contact_id = existing.get("id") if isinstance(existing, dict) else None
                if contact_id:
                    status, body = await self._request(
                        "PATCH",
                        f"/crm/v3/objects/contacts/{contact_id}",
                        json_body={"properties": properties},
                    )
                    if status in (200, 201):
                        contact_status = "updated"
                    else:
                        return self._provider_error(status)
                else:
                    return self._provider_error(409)
            elif status not in (200, 201):
                return self._provider_error(status)
            else:
                contact_id = str(body.get("id") or "")
                contact_status = "created"

        if not contact_id:
            return self._provider_error(502)

        note_status, note_body = await self._request(
            "POST",
            "/crm/v3/objects/notes",
            json_body={
                "properties": {
                    "hs_timestamp": datetime.now(timezone.utc)
                    .isoformat(timespec="milliseconds")
                    .replace("+00:00", "Z"),
                    "hs_note_body": self._note_body(
                        caller_name=caller_name,
                        caller_email=email,
                        caller_phone=phone,
                        service_needed=service_needed,
                        issue_summary=issue_summary,
                        property_address=property_address,
                        urgency=urgency,
                        preferred_callback_window=preferred_callback_window,
                    ),
                },
                "associations": [
                    {
                        "to": {"id": contact_id},
                        "types": [
                            {
                                "associationCategory": "HUBSPOT_DEFINED",
                                "associationTypeId": 202,
                            }
                        ],
                    }
                ],
            },
        )
        note: dict[str, Any] = {
            "status": "created" if note_status in (200, 201) else "failed",
            "id": str(note_body.get("id")) if note_body.get("id") else None,
        }
        if note["status"] != "created":
            error_code = self._provider_error_code(note_status)
            retryable = note_status == 429 or note_status >= 500
            return {
                "status": "failed",
                "provider": "hubspot",
                "message": (
                    "The HubSpot contact was captured, but the service inquiry "
                    "note could not be added."
                ),
                "next_action": "retry_later" if retryable else "contact_support",
                "retryable": retryable,
                "error": {
                    "code": error_code,
                    "message": "The HubSpot inquiry note could not be added.",
                    "next_action": "retry_later" if retryable else "contact_support",
                    "retryable": retryable,
                },
                "crm": {
                    "provider": "hubspot",
                    "record_type": "contact",
                    "record_id": contact_id,
                },
                "lead": {
                    "id": contact_id,
                    "name": caller_name.strip(),
                    "email": email or None,
                },
                "note": note,
            }
        return {
            "status": contact_status,
            "provider": "hubspot",
            "message": (
                "Service inquiry captured in HubSpot."
                if note["status"] == "created"
                else "Contact captured in HubSpot, but the inquiry note could not be added."
            ),
            "crm": {
                "provider": "hubspot",
                "record_type": "contact",
                "record_id": contact_id,
            },
            "lead": {
                "id": contact_id,
                "name": caller_name.strip(),
                "email": email or None,
            },
            "note": note,
            "note_error": (
                self._provider_error_code(note_status)
                if note["status"] == "failed"
                else None
            ),
        }

    async def _find_contact(
        self, property_name: str, value: str
    ) -> Optional[dict[str, Any]]:
        """Find one contact by a stable standard property."""
        status, body = await self._request(
            "POST",
            "/crm/v3/objects/contacts/search",
            json_body={
                "filterGroups": [
                    {
                        "filters": [
                            {
                                "propertyName": property_name,
                                "operator": "EQ",
                                "value": value,
                            }
                        ]
                    }
                ],
                "limit": 1,
                "properties": ["firstname", "lastname", "email", "phone", "address"],
            },
        )
        if status != 200:
            return self._provider_error(status)
        results = body.get("results") if isinstance(body, dict) else None
        if isinstance(results, list) and results and isinstance(results[0], dict):
            return {"id": str(results[0].get("id") or "")}
        return None

    async def _request(
        self, method: str, path: str, *, json_body: dict[str, Any]
    ) -> tuple[int, dict[str, Any]]:
        """Make one bounded HubSpot request without exposing response details."""
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        try:
            async with self.client_factory() as client:
                response = await client.request(
                    method,
                    f"{self.base_url}{path}",
                    headers=headers,
                    json=json_body,
                )
        except (httpx.TimeoutException, httpx.NetworkError):
            return 503, {}
        except Exception:
            return 500, {}
        try:
            body = response.json() if response.content else {}
        except ValueError:
            body = {}
        return response.status_code, body if isinstance(body, dict) else {}

    @staticmethod
    def _validate(
        *,
        caller_name: str,
        caller_email: str,
        caller_phone: str,
        service_needed: str,
        issue_summary: str,
    ) -> Optional[dict[str, Any]]:
        """Validate the minimum lead fields before any provider request."""
        if not caller_name.strip():
            return HubSpotLeadService._input_error(
                "caller_name", "Ask for the caller's name."
            )
        if not service_needed.strip():
            return HubSpotLeadService._input_error(
                "service_needed", "Ask what service is needed."
            )
        if not issue_summary.strip():
            return HubSpotLeadService._input_error(
                "issue_summary", "Ask for a short description of the issue."
            )
        if not caller_email.strip() and not caller_phone.strip():
            return HubSpotLeadService._input_error(
                "caller_email",
                "Ask for an email address or phone number so the inquiry can be followed up.",
            )
        if caller_email.strip() and not _EMAIL_PATTERN.match(caller_email.strip()):
            return HubSpotLeadService._input_error(
                "caller_email", "Ask for a valid email address."
            )
        return None

    @staticmethod
    def _input_error(field: str, message: str) -> dict[str, Any]:
        """Build a model-actionable validation result."""
        return {
            "status": "needs_details",
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

    @staticmethod
    def _contact_properties(
        *, caller_name: str, caller_email: str, caller_phone: str, property_address: str
    ) -> dict[str, str]:
        """Map the common lead details to standard HubSpot contact fields."""
        parts = caller_name.strip().split()
        properties = {
            "firstname": parts[0],
            "lastname": " ".join(parts[1:]) if len(parts) > 1 else "",
            "lifecyclestage": "lead",
        }
        if caller_email:
            properties["email"] = caller_email
        if caller_phone:
            properties["phone"] = caller_phone
        if property_address.strip():
            properties["address"] = property_address.strip()
        return {key: value for key, value in properties.items() if value}

    def _note_body(
        self,
        *,
        caller_name: str,
        caller_email: str,
        caller_phone: str,
        service_needed: str,
        issue_summary: str,
        property_address: str,
        urgency: str,
        preferred_callback_window: str,
    ) -> str:
        """Render the full, human-readable inquiry for the associated note."""
        lines = [
            "Voice service inquiry captured by 24x7 AI",
            f"Lead source: {self.lead_source}",
            f"Name: {caller_name.strip()}",
            f"Service needed: {service_needed.strip()}",
            f"Issue summary: {issue_summary.strip()}",
        ]
        optional = (
            ("Email", caller_email),
            ("Phone", caller_phone),
            ("Property address", property_address),
            ("Urgency", urgency),
            ("Preferred callback window", preferred_callback_window),
        )
        lines.extend(
            f"{label}: {value.strip()}" for label, value in optional if value.strip()
        )
        return "\n".join(lines)

    @staticmethod
    def _provider_error_code(status_code: int) -> str:
        """Map an HTTP status to a stable safe error code."""
        if status_code in (401, 403):
            return "authentication_required"
        if status_code == 429 or status_code >= 500:
            return "temporary_failure"
        return "provider_rejected"

    @classmethod
    def _provider_error(cls, status_code: int) -> dict[str, Any]:
        """Build an actionable but response-body-free provider error."""
        code = cls._provider_error_code(status_code)
        message = {
            "authentication_required": "HubSpot is not connected for this agent.",
            "temporary_failure": "HubSpot is temporarily unavailable. Please try again.",
            "provider_rejected": "HubSpot rejected the service inquiry. Please verify the details.",
        }[code]
        return {
            "status": "error",
            "provider": "hubspot",
            "message": message,
            "next_action": (
                "reauthorize" if code == "authentication_required" else "retry_later"
            ),
            "error": {
                "code": code,
                "message": message,
                "next_action": (
                    "reauthorize"
                    if code == "authentication_required"
                    else "retry_later"
                ),
                "retryable": code == "temporary_failure",
            },
        }


__all__ = ["HubSpotLeadService"]
