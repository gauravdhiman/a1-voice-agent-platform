"""Safe, configured Google Sheets row operations for native voice tools.

The service deliberately exposes a row-oriented contract instead of making the
model construct arbitrary A1 ranges or spreadsheet ids.  An agent attachment
owns the destination, the working range, and optional generated columns.  The
model supplies values keyed by the sheet's header names; the service validates
those keys, limits model-visible reads to the configured Agent fields and
managed columns, performs bounded reads, and requires an exact single-row match
for updates.
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any, Optional
from urllib.parse import quote

import httpx

from shared.voice_agents.tools.base.tool_context import ToolContext

logger = logging.getLogger(__name__)

_API_BASE = "https://sheets.googleapis.com/v4"
_TIMEOUT = 20.0
_MAX_ROWS = 100
_MAX_COLUMNS = 100
_MAX_CELL_LENGTH = 4000
_SPREADSHEET_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{10,}$")
_A1_RANGE_PATTERN = re.compile(
    r"^(?P<sheet>'(?:[^']|'')+'|[A-Za-z0-9][A-Za-z0-9 _-]{0,99})!"
    r"(?P<body>[A-Z]{1,3}\d*(?::[A-Z]{1,3}\d*)?)$"
)
_CELL_PATTERN = re.compile(r"^(?P<column>[A-Z]{1,3})(?P<row>\d*)$")


class GoogleSheetsService:
    """Execute bounded, header-aware row operations against one sheet area."""

    def __init__(
        self,
        *,
        access_token: str,
        spreadsheet_id: str,
        default_range: str = "Sheet1!A1:Z1000",
        header_range: str = "",
        agent_columns: str = "",
        idempotency_column: str = "",
        timestamp_column: str = "",
        source_column: str = "",
        source_value: str = "",
        status_column: str = "",
        status_value: str = "",
        required_columns: str = "",
        record_label: str = "spreadsheet row",
        client_factory: Optional[Callable[[], httpx.AsyncClient]] = None,
    ) -> None:
        self.access_token = access_token.strip()
        self.spreadsheet_id = self.extract_spreadsheet_id(spreadsheet_id)
        self.default_range = default_range.strip() or "Sheet1!A1:Z1000"
        self.header_range = header_range.strip()
        self.agent_columns = self._split_columns(agent_columns)
        self.idempotency_column = idempotency_column.strip()
        self.timestamp_column = timestamp_column.strip()
        self.source_column = source_column.strip()
        self.source_value = source_value.strip()[:200]
        self.status_column = status_column.strip()
        self.status_value = status_value.strip()[:200]
        self.required_columns = required_columns.strip()
        self.record_label = record_label.strip()[:80] or "spreadsheet row"
        self.client_factory = client_factory or self._default_client_factory

    @staticmethod
    def _default_client_factory() -> httpx.AsyncClient:
        """Create the bounded production HTTP client."""
        return httpx.AsyncClient(timeout=_TIMEOUT)

    @staticmethod
    def extract_spreadsheet_id(value: str) -> str:
        """Normalize a Sheets URL or bare id to the provider resource id."""
        candidate = str(value or "").strip()
        marker = "/spreadsheets/d/"
        if marker in candidate:
            candidate = candidate.split(marker, 1)[1].split("/", 1)[0]
            candidate = candidate.split("?", 1)[0].split("#", 1)[0]
        return candidate

    def configuration_issues(self) -> list[str]:
        """Return attachment configuration gaps without contacting Google."""
        issues: list[str] = []
        if len(self.spreadsheet_id) > 200 or not _SPREADSHEET_ID_PATTERN.fullmatch(
            self.spreadsheet_id
        ):
            issues.append("spreadsheet destination is not set")
        if not self._valid_range(self.default_range):
            issues.append("default sheet range is invalid")
        if not self._business_agent_columns():
            issues.append("agent fields are not set")
        if self.header_range and not self._valid_range(self.header_range):
            issues.append("header range is invalid")
        if self.header_range and self._valid_range(self.header_range):
            if (
                self._sheet_name(self.header_range).casefold()
                != self._sheet_name(self.default_range).casefold()
            ):
                issues.append("header range must use the configured sheet tab")
            elif not self._columns_within_configured_range(
                self.header_range
            ) or not self._rows_within_configured_range(self.header_range):
                issues.append(
                    "header range must stay within the configured working area"
                )
        if self.source_value and not self.source_column:
            issues.append("source column is not set")
        if self.status_value and not self.status_column:
            issues.append("status column is not set")
        for label, column in (
            ("idempotency", self.idempotency_column),
            ("timestamp", self.timestamp_column),
            ("status", self.status_column),
        ):
            if column and len(column) > 120:
                issues.append(f"{label} column is invalid")
        duplicate_agent_columns = self._duplicate_columns(self.agent_columns)
        if duplicate_agent_columns:
            issues.append("agent fields contain duplicate headers")
        duplicate_managed_columns = self._duplicate_columns(
            self._managed_column_names()
        )
        if duplicate_managed_columns:
            issues.append("managed columns must use different headers")
        managed_keys = self._managed_column_keys()
        overlapping_agent_columns = [
            column
            for column in self.agent_columns
            if self._canonical(column) in managed_keys
        ]
        if overlapping_agent_columns:
            issues.append(
                "managed columns must be removed from Agent fields: "
                + ", ".join(overlapping_agent_columns)
            )
        if self.agent_columns:
            agent_column_keys = {self._canonical(item) for item in self.agent_columns}
            missing_required = [
                item
                for item in self._business_required_columns()
                if self._canonical(item) not in agent_column_keys
            ]
            if missing_required:
                issues.append("required fields must be included in agent fields")
        return issues

    def model_function_guidance(self, function_name: str) -> str:
        """Return safe attachment-specific field guidance for the model.

        The destination id, OAuth token, and raw provider response remain
        private.  Only the administrator-selected business headers and the
        generated-field behavior are described to the model.
        """
        if not self._business_agent_columns():
            return ""

        business_fields = self._business_agent_columns()
        fields = ", ".join(f"`{column}`" for column in business_fields)
        required = (
            self._business_required_columns() if function_name == "create_row" else []
        )
        required_text = (
            " Required for create_row: "
            + ", ".join(f"`{item}`" for item in required)
            + ". Include a non-empty value for every required field before "
            "calling; if one is not confirmed, ask for it instead of guessing."
            if required
            else ""
        )
        generated: list[str] = []
        for label, column in (
            ("idempotency key", self.idempotency_column),
            ("timestamp", self.timestamp_column),
            ("source", self.source_column if self.source_value else ""),
            ("initial status", self.status_column if self.status_value else ""),
        ):
            if column:
                generated.append(f"`{column}` ({label})")
        generated_text = ""
        if generated:
            generated_text = (
                " The attachment manages "
                + ", ".join(generated)
                + "; do not invent or overwrite those values during create_row."
            )
        retry_text = (
            " If the result is retryable `needs_details`, correct the missing "
            "field or exact header once and retry; never claim success without a "
            "successful result."
            if function_name == "create_row"
            else ""
        )

        if function_name == "create_row":
            action = (
                "Pass business data in the `values` object using only these exact "
                "header keys; do not rename them, convert them to snake_case, or "
                "invent additional keys."
            )
        elif function_name == "read_rows":
            action = "Returned row objects use these exact header names as keys."
        elif function_name == "find_rows":
            action = "Use one of these headers when narrowing a search by column."
        elif function_name == "update_row":
            action = (
                "Use these exact headers for the match column; values may contain "
                "only business Agent fields and may be partial."
            )
        else:
            action = "Use these exact header names when working with rows."

        return (
            f"Configured agent fields: {fields}. {action}"
            f" Header spelling is normalized only at the service boundary; send "
            f"the exact configured names.{required_text}{generated_text}{retry_text}"
        )

    def model_function_properties(
        self,
        function_name: str,
        properties: dict[str, Any],
    ) -> dict[str, Any]:
        """Close row-value schemas around the administrator-selected headers.

        The catalog must remain generic because every sheet has different
        columns. Once an attachment is configured, the runtime can provide a
        precise object schema to the model. This prevents common variants such
        as ``Caller_Name`` or ``Order_details`` from reaching the provider and
        marks the configured required business fields as required in
        ``create_row`` calls.
        """
        business_fields = self._business_agent_columns()
        if not business_fields:
            return properties

        scalar_schema = {
            "anyOf": [
                {"type": "string"},
                {"type": "number"},
                {"type": "boolean"},
            ]
        }
        values_schema: dict[str, Any] = {
            "type": "object",
            "properties": {field: dict(scalar_schema) for field in business_fields},
            "additionalProperties": False,
        }
        if function_name == "create_row":
            required = self._business_required_columns()
            if required:
                values_schema["required"] = required

        updated = dict(properties)
        if function_name in {"create_row", "update_row"} and "values" in updated:
            updated["values"] = values_schema

        configured_headers = [
            *business_fields,
            *self._managed_column_names(),
        ]
        if function_name == "update_row" and "match_column" in updated:
            updated["match_column"] = {
                "type": "string",
                "enum": configured_headers,
            }
        if function_name == "find_rows" and "column" in updated:
            updated["column"] = {
                "type": "string",
                # ``column`` is optional; omitting it already means search all
                # columns. Empty-string sentinel values are rejected by Gemini
                # Live's function-schema validator.
                "enum": configured_headers,
            }
        return updated

    async def read_rows(
        self,
        *,
        context: ToolContext,
        range: str = "",
        max_rows: int = 50,
    ) -> dict[str, Any]:
        """Read a bounded set of rows as objects keyed by sheet headers.

        The configured range and spreadsheet are authoritative.  A caller may
        narrow the range to the same configured tab, but cannot redirect the
        operation to another spreadsheet or tab.
        """
        setup_error = self._validate_connection()
        if setup_error:
            return setup_error
        if range and not isinstance(range, str):
            return self._input_error("range", "range must be text in A1 notation.")
        resolved_range = self._resolve_range(range)
        if isinstance(resolved_range, dict):
            return resolved_range
        try:
            bounded_rows = int(max_rows)
        except (TypeError, ValueError):
            return self._input_error(
                "max_rows", "max_rows must be a whole number between 1 and 100."
            )
        if bounded_rows < 1 or bounded_rows > _MAX_ROWS:
            return self._input_error(
                "max_rows", "max_rows must be a whole number between 1 and 100."
            )
        headers, header_error = await self._read_headers()
        if header_error:
            return header_error
        configuration_error = self._validate_configured_headers(headers)
        if configuration_error:
            return configuration_error
        values_result = await self._read_values(resolved_range)
        if values_result[0] != 200:
            return self._provider_error(values_result[0], "read rows")
        values = values_result[1].get("values", [])
        start_row = self._range_start_row(resolved_range)
        header_row = self._range_start_row(self._effective_header_range())
        all_rows = self._rows_from_values(
            headers,
            values,
            start_row=start_row,
            header_row=header_row,
        )
        visible_headers = [
            header
            for header in headers
            if self._canonical(header) in self._model_column_keys()
        ]
        rows = []
        for row in all_rows:
            visible_row = {header: row.get(header, "") for header in visible_headers}
            if not any(str(value).strip() for value in visible_row.values()):
                continue
            visible_row["row_number"] = row["row_number"]
            rows.append(visible_row)
        truncated = len(rows) > bounded_rows
        return {
            "status": "succeeded",
            "provider": "google_sheets",
            "range": resolved_range,
            "headers": visible_headers,
            "rows": rows[:bounded_rows],
            "row_count": min(len(rows), bounded_rows),
            "truncated": truncated,
        }

    async def discover_sheet_headers(
        self,
        *,
        max_sheets: int = 20,
        max_columns: int = _MAX_COLUMNS,
    ) -> dict[str, Any]:
        """Return the first-row headers for the connected spreadsheet tabs.

        This is a read-only setup operation for the agent-tool editor.  It
        intentionally returns tab names and header labels only; cell data and
        provider response bodies never leave the service boundary.  Empty tabs
        are returned with an actionable issue so administrators can choose a
        different tab or add a header row without guessing A1 ranges.
        """
        if not isinstance(max_sheets, int) or not 1 <= max_sheets <= 50:
            return self._input_error(
                "max_sheets", "max_sheets must be a whole number between 1 and 50."
            )
        if not isinstance(max_columns, int) or not 1 <= max_columns <= _MAX_COLUMNS:
            return self._input_error(
                "max_columns",
                f"max_columns must be a whole number between 1 and {_MAX_COLUMNS}.",
            )
        if len(self.spreadsheet_id) > 200 or not _SPREADSHEET_ID_PATTERN.fullmatch(
            self.spreadsheet_id
        ):
            return self._config_error("spreadsheet destination is not set")
        if not self.access_token:
            return self._error(
                "authentication_required",
                "Google Sheets authorization is not connected for this agent.",
                next_action="reauthorize",
                retryable=False,
            )

        status, body = await self._request(
            "GET",
            f"/spreadsheets/{self.spreadsheet_id}",
            params={"fields": "sheets.properties(title,sheetId)"},
        )
        if status != 200:
            return self._provider_error(status, "list sheet tabs")

        raw_sheets = body.get("sheets", []) if isinstance(body, dict) else []
        if not isinstance(raw_sheets, list):
            raw_sheets = []

        sheets: list[dict[str, Any]] = []
        header_end = self._column_letters(max_columns)
        for raw_sheet in raw_sheets[:max_sheets]:
            properties = (
                raw_sheet.get("properties", {}) if isinstance(raw_sheet, dict) else {}
            )
            if not isinstance(properties, dict):
                continue
            title = self._value_text(properties.get("title")).strip()
            if not title or len(title) > 100:
                continue
            try:
                sheet_id = int(properties.get("sheetId"))
            except (TypeError, ValueError):
                sheet_id = None
            header_range = self._discovery_header_range(title, header_end)
            header_status, header_body = await self._read_values(header_range)
            if header_status != 200:
                sheets.append(
                    {
                        "title": title,
                        "sheet_id": sheet_id,
                        "headers": [],
                        "header_range": header_range,
                        "issues": ["The header row could not be read for this tab."],
                    }
                )
                continue

            values = (
                header_body.get("values", []) if isinstance(header_body, dict) else []
            )
            first_row = values[0] if isinstance(values, list) and values else []
            raw_headers = first_row if isinstance(first_row, list) else []
            headers = [self._value_text(value).strip() for value in raw_headers]
            headers = headers[:max_columns]
            issues: list[str] = []
            if not any(headers):
                headers = []
                issues.append(
                    "Add a header row to this tab before configuring the agent."
                )
            else:
                if any(not header for header in headers):
                    issues.append(
                        "Every header cell before the last column needs a name."
                    )
                if len(
                    {self._canonical(header) for header in headers if header}
                ) != len([header for header in headers if header]):
                    issues.append(
                        "Header names must be unique, ignoring case and spacing."
                    )
            sheets.append(
                {
                    "title": title,
                    "sheet_id": sheet_id,
                    "headers": headers,
                    "header_range": header_range,
                    "issues": issues,
                }
            )

        return {
            "status": "succeeded",
            "provider": "google_sheets",
            "sheets": sheets,
        }

    async def find_rows(
        self,
        *,
        context: ToolContext,
        query: str,
        column: str = "",
        range: str = "",
        max_results: int = 20,
    ) -> dict[str, Any]:
        """Find rows containing ``query`` in one column or anywhere in a row."""
        if not isinstance(query, str) or not query.strip():
            return self._input_error("query", "Provide a value to search for.")
        if column and not isinstance(column, str):
            return self._input_error("column", "column must be a sheet header name.")
        if range and not isinstance(range, str):
            return self._input_error("range", "range must be text in A1 notation.")
        try:
            bounded_results = int(max_results)
        except (TypeError, ValueError):
            return self._input_error(
                "max_results", "max_results must be a whole number between 1 and 100."
            )
        if bounded_results < 1 or bounded_results > _MAX_ROWS:
            return self._input_error(
                "max_results", "max_results must be a whole number between 1 and 100."
            )
        read_result = await self.read_rows(
            context=context,
            range=range,
            max_rows=_MAX_ROWS,
        )
        if read_result.get("status") != "succeeded":
            return read_result
        headers = read_result.get("headers", [])
        canonical_headers = self._header_map(headers)
        requested_column = self._canonical(column)
        if column and requested_column not in self._model_column_keys():
            return self._input_error(
                "column",
                "Use one of the configured agent fields or managed columns.",
            )
        actual_column = canonical_headers.get(requested_column) if column else None
        if column and not actual_column:
            return self._unknown_column_error(column, headers)
        needle = query.strip().casefold()
        matches: list[dict[str, Any]] = []
        for row in read_result.get("rows", []):
            candidate_values = (
                [row.get(actual_column)]
                if actual_column
                else [row.get(header) for header in headers]
            )
            if any(
                needle in self._value_text(value).casefold()
                for value in candidate_values
            ):
                matches.append(row)
                if len(matches) >= bounded_results:
                    break
        return {
            "status": "succeeded",
            "provider": "google_sheets",
            "query": query.strip(),
            "column": actual_column,
            "rows": matches,
            "match_count": len(matches),
        }

    async def create_row(
        self,
        *,
        context: ToolContext,
        values: dict[str, Any],
    ) -> dict[str, Any]:
        """Validate and append one row keyed by configured header names.

        The service reads headers before writing, fills configured generated
        columns (session id, timestamp, source, and status), and performs a
        read-before-append when an idempotency column is configured.  A retry
        after an uncertain provider response therefore cannot create a second
        row for the same voice session.
        """
        setup_error = self._validate_connection()
        if setup_error:
            return setup_error
        if not isinstance(values, dict) or not values:
            return self._input_error("values", "Provide at least one column value.")
        headers, header_error = await self._read_headers()
        if header_error:
            return header_error
        configuration_error = self._validate_configured_headers(headers)
        if configuration_error:
            return configuration_error
        normalized, preparation_error = self._prepare_values(values, headers, context)
        if preparation_error:
            return preparation_error
        idempotency_value = normalized.get(
            self._header_map(headers).get(self._canonical(self.idempotency_column), "")
        )
        if self.idempotency_column and idempotency_value:
            existing = await self._find_exact_row(
                headers=headers,
                column=self.idempotency_column,
                value=idempotency_value,
            )
            if isinstance(existing, dict) and existing.get("error"):
                return existing
            if existing:
                return self._created_result(
                    record_id=idempotency_value,
                    updated_range=existing.get("updated_range"),
                    deduplicated=True,
                )
        row = [normalized.get(header, "") for header in headers]
        status, body = await self._append_row(row)
        if status != 200:
            return self._provider_error(status, "create row")
        updated_range = self._updated_range(body)
        return self._created_result(
            record_id=idempotency_value or updated_range or "row",
            updated_range=updated_range,
            deduplicated=False,
        )

    async def update_row(
        self,
        *,
        context: ToolContext,
        match_column: str,
        match_value: str,
        values: dict[str, Any],
    ) -> dict[str, Any]:
        """Update exactly one row found by an exact column/value match."""
        del context  # The provider operation is scoped by the attachment config.
        setup_error = self._validate_connection()
        if setup_error:
            return setup_error
        if (
            not isinstance(match_column, str)
            or not isinstance(match_value, str)
            or not match_column.strip()
            or not match_value.strip()
        ):
            return self._input_error(
                "match_value", "Provide both a match column and match value."
            )
        if not isinstance(values, dict) or not values:
            return self._input_error("values", "Provide at least one column update.")
        headers, header_error = await self._read_headers()
        if header_error:
            return header_error
        configuration_error = self._validate_configured_headers(headers)
        if configuration_error:
            return configuration_error
        header_map = self._header_map(headers)
        if self._canonical(match_column) not in self._model_column_keys():
            return self._input_error(
                "match_column",
                "Use one of the configured agent fields or managed columns.",
            )
        actual_match_column = header_map.get(self._canonical(match_column))
        if not actual_match_column:
            return self._unknown_column_error(match_column, headers)
        normalized, preparation_error = self._prepare_values(
            values,
            headers,
            ToolContext(),
            fill_generated=False,
            validate_required=False,
        )
        if preparation_error:
            return preparation_error
        if self.idempotency_column and self._canonical(self.idempotency_column) in {
            self._canonical(key) for key in values
        }:
            return self._input_error(
                "values", "The configured key column cannot be changed."
            )
        existing = await self._find_exact_row(
            headers=headers,
            column=actual_match_column,
            value=match_value.strip(),
        )
        if isinstance(existing, dict) and existing.get("error"):
            return existing
        if not existing:
            return self._not_found_error(
                f"No row matched {actual_match_column} = '{match_value.strip()}'."
            )
        if existing.get("ambiguous"):
            return self._conflict_error(
                f"More than one row matched {actual_match_column}; refusing a broad update."
            )
        row_values = list(existing["values"])
        for header, value in normalized.items():
            row_values[headers.index(header)] = value
        row_range = self._row_range(int(existing["row_number"]))
        status, body = await self._put_row(row_range, row_values)
        if status != 200:
            return self._provider_error(status, "update row")
        return {
            "status": "updated",
            "provider": "google_sheets",
            "message": f"{self.record_label.capitalize()} updated in Google Sheets.",
            "sheet": {
                "provider": "google_sheets",
                "record_type": "row",
                "record_label": self.record_label,
                "record_id": match_value.strip(),
                "updated_range": self._updated_range(body) or row_range,
            },
        }

    async def _read_headers(self) -> tuple[list[str], Optional[dict[str, Any]]]:
        """Read and validate one non-empty, unique header row."""
        header_range = self._effective_header_range()
        result = await self._read_values(header_range)
        if result[0] != 200:
            return [], self._provider_error(result[0], "read sheet headers")
        values = result[1].get("values", [])
        first_row = values[0] if values else []
        headers = [self._value_text(value).strip() for value in first_row]
        if not headers or not any(headers):
            return [], self._input_error(
                "headers",
                "The configured sheet must have a header row before rows can be managed.",
            )
        if len(headers) > _MAX_COLUMNS:
            return [], self._input_error(
                "headers",
                f"The configured sheet supports at most {_MAX_COLUMNS} columns.",
            )
        if any(not header for header in headers):
            return [], self._input_error(
                "headers", "Every configured data column needs a non-empty header."
            )
        if len({self._canonical(header) for header in headers}) != len(headers):
            return [], self._input_error(
                "headers", "Sheet headers must be unique, ignoring case and spacing."
            )
        return headers, None

    async def _find_exact_row(
        self,
        *,
        headers: list[str],
        column: str,
        value: str,
    ) -> Optional[dict[str, Any]]:
        """Find an exact row in the configured range without returning data."""
        range_result = await self._read_values(self.default_range)
        if range_result[0] != 200:
            return self._provider_error(range_result[0], "find row")
        actual_column = self._header_map(headers).get(self._canonical(column))
        if not actual_column:
            return self._unknown_column_error(column, headers)
        index = headers.index(actual_column)
        values = range_result[1].get("values", [])
        start_row = self._range_start_row(self.default_range)
        header_row = self._range_start_row(self._effective_header_range())
        matches: list[dict[str, Any]] = []
        for offset, raw_row in enumerate(values):
            row_number = start_row + offset
            if row_number == header_row:
                continue
            row = list(raw_row) + [""] * max(0, len(headers) - len(raw_row))
            candidate = self._value_text(row[index] if index < len(row) else "")
            if candidate == value:
                matches.append(
                    {
                        "row_number": row_number,
                        "values": row[: len(headers)],
                        "updated_range": f"{self._sheet_prefix(self.default_range)}!"
                        f"{self._column_for_range(self.default_range, 0)}{row_number}",
                    }
                )
        if len(matches) > 1:
            return {"ambiguous": True}
        return matches[0] if matches else None

    def _prepare_values(
        self,
        values: dict[str, Any],
        headers: list[str],
        context: ToolContext,
        *,
        fill_generated: bool = True,
        validate_required: bool = True,
    ) -> tuple[dict[str, str], Optional[dict[str, Any]]]:
        """Normalize model values, generated columns, and required fields."""
        header_map = self._header_map(headers)
        normalized: dict[str, str] = {}
        configured_agent_columns = {
            self._canonical(column) for column in self._business_agent_columns()
        }
        for key, value in values.items():
            if not isinstance(key, str) or not key.strip():
                return {}, self._input_error(
                    "values", "Column names must be non-empty text."
                )
            canonical_key = self._canonical(key)
            if canonical_key in self._managed_column_keys():
                return {}, self._input_error(
                    key,
                    (
                        "Managed columns are filled by the attachment; provide "
                        "business fields only."
                        if fill_generated
                        else "Managed columns cannot be changed by update_row."
                    ),
                )
            if (
                configured_agent_columns
                and canonical_key not in configured_agent_columns
            ):
                return {}, self._input_error(
                    key,
                    "Use one of the configured agent fields: "
                    + ", ".join(self._business_agent_columns()),
                )
            actual = header_map.get(self._canonical(key))
            if not actual:
                return {}, self._unknown_column_error(key, headers)
            if isinstance(value, (dict, list, tuple, set)):
                return {}, self._input_error(
                    key, "Each cell must be a text, number, boolean, or empty value."
                )
            text = self._value_text(value)
            if len(text) > _MAX_CELL_LENGTH:
                return {}, self._input_error(
                    key, f"Keep cell values to {_MAX_CELL_LENGTH} characters or fewer."
                )
            normalized[actual] = text

        if fill_generated and self.idempotency_column and not context.session_id:
            return {}, self._config_error(
                "A voice session id is required for idempotent row creation."
            )

        if fill_generated:
            generated = (
                (self.idempotency_column, context.session_id),
                (
                    self.timestamp_column,
                    (context.current_time or datetime.now(timezone.utc))
                    .astimezone(timezone.utc)
                    .isoformat(timespec="seconds")
                    .replace("+00:00", "Z"),
                ),
                (self.source_column, self.source_value),
                (self.status_column, self.status_value),
            )
            for configured_column, generated_value in generated:
                if not configured_column or not generated_value:
                    continue
                actual = header_map.get(self._canonical(configured_column))
                if not actual:
                    return {}, self._unknown_column_error(configured_column, headers)
                existing = normalized.get(actual, "")
                if configured_column == self.idempotency_column:
                    if not context.session_id:
                        return {}, self._config_error(
                            "A voice session id is required for idempotent row creation."
                        )
                    if existing and existing != str(generated_value):
                        return {}, self._input_error(
                            configured_column,
                            "The idempotency column is managed by the active session.",
                        )
                if not existing:
                    normalized[actual] = str(generated_value)

        if validate_required:
            required = self._business_required_columns()
            missing_required: list[str] = []
            for required_column in required:
                actual = header_map.get(self._canonical(required_column))
                if not actual:
                    return {}, self._unknown_column_error(required_column, headers)
                if not normalized.get(actual, "").strip():
                    missing_required.append(actual)
            if missing_required:
                return {}, self._input_error(
                    "values",
                    "Provide a value for every required column before saving: "
                    + ", ".join(missing_required)
                    + ".",
                )
        return normalized, None

    async def _read_values(self, a1_range: str) -> tuple[int, dict[str, Any]]:
        """Read one validated range from the Sheets values API."""
        return await self._request(
            "GET",
            f"/spreadsheets/{self.spreadsheet_id}/values/{self._encoded_range(a1_range)}",
        )

    async def _append_row(self, values: list[str]) -> tuple[int, dict[str, Any]]:
        """Append exactly one row to the configured range."""
        return await self._request(
            "POST",
            f"/spreadsheets/{self.spreadsheet_id}/values/{self._encoded_range(self.default_range)}:append",
            params={"valueInputOption": "RAW", "insertDataOption": "INSERT_ROWS"},
            json_body={"values": [values]},
        )

    async def _put_row(
        self, row_range: str, values: list[str]
    ) -> tuple[int, dict[str, Any]]:
        """Replace one previously matched row without touching neighbors."""
        return await self._request(
            "PUT",
            f"/spreadsheets/{self.spreadsheet_id}/values/{self._encoded_range(row_range)}",
            params={"valueInputOption": "RAW"},
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
        """Perform one bounded provider call without exposing response bodies."""
        if not self.access_token:
            return 401, {}
        client: Optional[httpx.AsyncClient] = None
        try:
            client = self.client_factory()
            response = await client.request(
                method,
                f"{_API_BASE}{path}",
                params=params,
                json=json_body,
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
            )
            try:
                body = response.json() if response.content else {}
            except ValueError:
                body = {}
            return response.status_code, body if isinstance(body, dict) else {}
        except httpx.HTTPError as exc:
            logger.warning(
                "Google Sheets request failed method=%s error=%s",
                method,
                type(exc).__name__,
            )
            return 0, {}
        except Exception as exc:  # noqa: BLE001 - provider boundary must be safe
            logger.warning(
                "Google Sheets request failed method=%s error=%s",
                method,
                type(exc).__name__,
            )
            return 0, {}
        finally:
            if client is not None:
                await client.aclose()

    def _validate_connection(self) -> Optional[dict[str, Any]]:
        """Validate provider credentials and destination before I/O."""
        issues = self.configuration_issues()
        if issues:
            return self._config_error(issues[0])
        if not self.access_token:
            return self._error(
                "authentication_required",
                "Google Sheets authorization is not connected for this agent.",
                next_action="reauthorize",
                retryable=False,
            )
        return None

    def _resolve_range(self, candidate: str) -> str | dict[str, Any]:
        """Resolve a narrowed range while keeping the configured tab boundary."""
        resolved = candidate.strip() if candidate else self.default_range
        if not self._valid_range(resolved):
            return self._input_error(
                "range", "Use a valid A1 range such as Orders!A:L."
            )
        if (
            self._sheet_name(resolved).casefold()
            != self._sheet_name(self.default_range).casefold()
        ):
            return self._input_error(
                "range", "The requested range must use the configured sheet tab."
            )
        if not self._columns_within_configured_range(resolved):
            return self._input_error(
                "range",
                "The requested range must stay within the configured working area.",
            )
        if not self._rows_within_configured_range(resolved):
            return self._input_error(
                "range",
                "The requested range must stay within the configured working area.",
            )
        return resolved

    def _effective_header_range(self) -> str:
        """Return the configured header range or derive row one from the data range."""
        if self.header_range:
            return self.header_range
        sheet = self._sheet_prefix(self.default_range)
        body = self.default_range.split("!", 1)[1]
        start, end = self._range_columns(body)
        return f"{sheet}!{start}1:{end}1"

    @classmethod
    def _discovery_header_range(cls, sheet_title: str, end_column: str) -> str:
        """Build a bounded first-row range for a discovered sheet title."""
        escaped = sheet_title.replace("'", "''")
        return f"'{escaped}'!A1:{end_column}1"

    def _row_range(self, row_number: int) -> str:
        start, end = self._range_columns(self.default_range.split("!", 1)[1])
        return f"{self._sheet_prefix(self.default_range)}!{start}{row_number}:{end}{row_number}"

    @staticmethod
    def _rows_from_values(
        headers: list[str],
        values: list[Any],
        *,
        start_row: int,
        header_row: int,
    ) -> list[dict[str, Any]]:
        """Convert a provider matrix into bounded row objects."""
        rows: list[dict[str, Any]] = []
        for offset, raw_row in enumerate(values):
            row_number = start_row + offset
            if row_number == header_row:
                continue
            row = list(raw_row) if isinstance(raw_row, list) else []
            padded = row + [""] * max(0, len(headers) - len(row))
            values_by_header = {
                header: padded[index] if index < len(padded) else ""
                for index, header in enumerate(headers)
            }
            if not any(str(value).strip() for value in values_by_header.values()):
                continue
            values_by_header["row_number"] = row_number
            rows.append(values_by_header)
        return rows

    @staticmethod
    def _header_map(headers: list[str]) -> dict[str, str]:
        """Map normalized header labels back to their exact sheet spelling."""
        return {GoogleSheetsService._canonical(header): header for header in headers}

    def _model_column_keys(self) -> set[str]:
        """Return canonical agent-visible and managed column names."""
        return {
            self._canonical(column)
            for column in (
                *self.agent_columns,
                self.idempotency_column,
                self.timestamp_column,
                self.source_column,
                self.status_column,
            )
            if column
        }

    def _managed_column_names(self) -> list[str]:
        """Return configured platform-managed headers in stable display order."""
        return [
            column
            for column in (
                self.idempotency_column,
                self.timestamp_column,
                self.source_column,
                self.status_column,
            )
            if column
        ]

    def _managed_column_keys(self) -> set[str]:
        """Return canonical names for headers populated by the attachment."""
        return {self._canonical(column) for column in self._managed_column_names()}

    def _business_agent_columns(self) -> list[str]:
        """Return model-populated fields, excluding generated metadata columns."""
        managed = self._managed_column_keys()
        return [
            column
            for column in self.agent_columns
            if self._canonical(column) not in managed
        ]

    def _business_required_columns(self) -> list[str]:
        """Return required model fields, excluding generated metadata columns."""
        managed = self._managed_column_keys()
        return [
            column
            for column in self._split_columns(self.required_columns)
            if self._canonical(column) not in managed
        ]

    def _validate_configured_headers(
        self, headers: list[str]
    ) -> Optional[dict[str, Any]]:
        """Fail clearly when saved field mappings no longer match the tab."""
        available = {self._canonical(header) for header in headers}
        missing: list[str] = []
        seen: set[str] = set()
        configured = [
            *self._business_agent_columns(),
            *self._business_required_columns(),
            *self._managed_column_names(),
        ]
        for column in configured:
            key = self._canonical(column)
            if key and key not in available and key not in seen:
                missing.append(column)
                seen.add(key)
        if not missing:
            return None
        message = (
            "Configured Google Sheets columns are not present in the selected tab: "
            + ", ".join(missing)
            + ". Re-discover the columns and save the attachment configuration."
        )
        return self._config_error(message)

    @staticmethod
    def _split_columns(value: str) -> list[str]:
        """Parse a comma-separated column setting while preserving spelling."""
        columns: list[str] = []
        for item in str(value or "").split(","):
            column = " ".join(item.strip().split())
            if column:
                columns.append(column)
        return columns

    @classmethod
    def _duplicate_columns(cls, columns: list[str]) -> list[str]:
        """Return duplicate configured headers using canonical comparison."""
        duplicates: list[str] = []
        seen: set[str] = set()
        for column in columns:
            key = cls._canonical(column)
            if key in seen:
                duplicates.append(column)
            seen.add(key)
        return duplicates

    @staticmethod
    def _canonical(value: str) -> str:
        """Normalize header labels for case/spacing-insensitive matching."""
        return " ".join(str(value or "").strip().split()).casefold()

    @staticmethod
    def _value_text(value: Any) -> str:
        """Convert scalar provider/model values to one bounded cell string."""
        if value is None:
            return ""
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, (dict, list, tuple, set)):
            return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        return str(value)

    @staticmethod
    def _sheet_name(a1_range: str) -> str:
        return a1_range.split("!", 1)[0].strip().strip("'").replace("''", "'")

    @staticmethod
    def _sheet_prefix(a1_range: str) -> str:
        return a1_range.split("!", 1)[0].strip()

    @staticmethod
    def _range_columns(body: str) -> tuple[str, str]:
        cells = body.split(":", 1)
        start_match = _CELL_PATTERN.fullmatch(cells[0])
        end_match = _CELL_PATTERN.fullmatch(cells[-1])
        if not start_match or not end_match:
            return "A", "Z"
        return start_match.group("column"), end_match.group("column")

    def _columns_within_configured_range(self, candidate: str) -> bool:
        """Return whether a range stays inside the configured column bounds."""
        try:
            configured_start, configured_end = self._range_columns(
                self.default_range.split("!", 1)[1]
            )
            candidate_start, candidate_end = self._range_columns(
                candidate.split("!", 1)[1]
            )
            return (
                self._column_number(configured_start)
                <= self._column_number(candidate_start)
                <= self._column_number(candidate_end)
                <= self._column_number(configured_end)
            )
        except (IndexError, ValueError):
            return False

    def _rows_within_configured_range(self, candidate: str) -> bool:
        """Return whether a range stays inside the configured row bounds."""
        try:
            configured_start, configured_end = self._range_rows(
                self.default_range.split("!", 1)[1]
            )
            candidate_start, candidate_end = self._range_rows(
                candidate.split("!", 1)[1]
            )
            if candidate_start < configured_start:
                return False
            if configured_end is not None and (
                candidate_end is None or candidate_end > configured_end
            ):
                return False
            return True
        except (IndexError, ValueError):
            return False

    @staticmethod
    def _range_rows(body: str) -> tuple[int, Optional[int]]:
        """Extract inclusive row bounds; ``None`` means the range is open-ended."""
        cells = body.split(":", 1)
        start_match = _CELL_PATTERN.fullmatch(cells[0])
        end_match = _CELL_PATTERN.fullmatch(cells[-1])
        if not start_match or not end_match:
            raise ValueError("invalid A1 range")
        start = int(start_match.group("row") or 1)
        end_text = end_match.group("row")
        end = int(end_text) if end_text else None
        if end is not None and end < start:
            raise ValueError("invalid A1 row bounds")
        return start, end

    @staticmethod
    def _range_start_row(a1_range: str) -> int:
        body = a1_range.split("!", 1)[1]
        start = body.split(":", 1)[0]
        match = _CELL_PATTERN.fullmatch(start)
        return int(match.group("row") or 1) if match else 1

    @classmethod
    def _column_for_range(cls, a1_range: str, offset: int) -> str:
        start, _ = cls._range_columns(a1_range.split("!", 1)[1])
        return cls._column_letters(cls._column_number(start) + offset)

    @staticmethod
    def _column_number(column: str) -> int:
        value = 0
        for character in column:
            value = value * 26 + ord(character) - ord("A") + 1
        return value

    @staticmethod
    def _column_letters(number: int) -> str:
        result = ""
        while number:
            number, remainder = divmod(number - 1, 26)
            result = chr(65 + remainder) + result
        return result or "A"

    @staticmethod
    def _valid_range(value: str) -> bool:
        return bool(value and len(value) <= 200 and _A1_RANGE_PATTERN.fullmatch(value))

    @staticmethod
    def _encoded_range(value: str) -> str:
        return quote(value, safe="!:$'()")

    @staticmethod
    def _updated_range(body: dict[str, Any]) -> Optional[str]:
        updates = body.get("updates") if isinstance(body, dict) else None
        if isinstance(updates, dict):
            value = updates.get("updatedRange")
            return str(value) if value else None
        value = body.get("updatedRange") if isinstance(body, dict) else None
        return str(value) if value else None

    def _created_result(
        self,
        *,
        record_id: str,
        updated_range: Optional[str],
        deduplicated: bool,
    ) -> dict[str, Any]:
        """Return the stable generic row-creation result."""
        return {
            "status": "created",
            "provider": "google_sheets",
            "message": (
                f"{self.record_label.capitalize()} was already present in Google Sheets."
                if deduplicated
                else f"{self.record_label.capitalize()} saved in Google Sheets."
            ),
            "sheet": {
                "provider": "google_sheets",
                "record_type": "row",
                "record_label": self.record_label,
                "record_id": record_id,
                "updated_range": updated_range,
            },
            "deduplicated": deduplicated,
        }

    def _unknown_column_error(self, column: str, headers: list[str]) -> dict[str, Any]:
        return self._input_error(
            "column",
            f"Unknown sheet column '{column}'. Use one of: {', '.join(headers)}.",
        )

    @staticmethod
    def _input_error(field: str, message: str) -> dict[str, Any]:
        return {
            "status": "needs_details",
            "provider": "google_sheets",
            "message": message,
            "next_action": "correct_tool_arguments",
            "error": {
                "code": "invalid_input",
                "field": field,
                "message": message,
                "next_action": "correct_tool_arguments",
                "retryable": True,
            },
        }

    @staticmethod
    def _config_error(message: str) -> dict[str, Any]:
        return {
            "status": "error",
            "provider": "google_sheets",
            "message": message,
            "next_action": "configure_tool",
            "error": {
                "code": "invalid_configuration",
                "message": message,
                "next_action": "configure_tool",
                "retryable": False,
            },
        }

    @staticmethod
    def _not_found_error(message: str) -> dict[str, Any]:
        return {
            "status": "not_found",
            "provider": "google_sheets",
            "message": message,
            "next_action": "verify_match",
            "error": {
                "code": "row_not_found",
                "message": message,
                "next_action": "verify_match",
                "retryable": True,
            },
        }

    @staticmethod
    def _conflict_error(message: str) -> dict[str, Any]:
        return {
            "status": "conflict",
            "provider": "google_sheets",
            "message": message,
            "next_action": "refine_match",
            "error": {
                "code": "ambiguous_match",
                "message": message,
                "next_action": "refine_match",
                "retryable": True,
            },
        }

    @classmethod
    def _provider_error(cls, status_code: int, operation: str) -> dict[str, Any]:
        if status_code in (401, 403):
            return cls._error(
                "authentication_required",
                "Google Sheets authorization is unavailable for this agent.",
                next_action="reauthorize",
                retryable=False,
            )
        if status_code == 404:
            return cls._error(
                "not_found",
                "The configured Google Sheet or tab could not be found.",
                next_action="configure_tool",
                retryable=False,
            )
        if status_code == 429 or status_code >= 500 or status_code == 0:
            return cls._error(
                "temporary_failure",
                f"Google Sheets is temporarily unavailable while trying to {operation}.",
                next_action="retry_later",
                retryable=True,
            )
        return cls._error(
            "provider_rejected",
            f"Google Sheets rejected the request to {operation}.",
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


__all__ = ["GoogleSheetsService"]
