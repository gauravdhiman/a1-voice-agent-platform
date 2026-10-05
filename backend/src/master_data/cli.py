"""Dry-run-first command-line workflow for platform master data.

The command is intentionally separate from application startup. Operators can
generate a reviewable JSON plan, inspect the exact source payloads, and apply
that same plan only after its definition hashes still match the checked-out
source.

Examples:
    ``python -m src.master_data.cli``
    ``python -m src.master_data.cli preview --format markdown --output master-data-review.md``
    ``python -m src.master_data.cli preview --format json --output master-data-plan.json``
    ``python -m src.master_data.cli apply --plan master-data-plan.json``
    ``python -m src.master_data.cli apply --plan master-data-plan.json --reset --yes``
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Sequence

from .definitions import SEED_DEFINITION_VERSION
from .service import RESET_ALLOWED_ENVIRONMENTS, MasterDataService

PLAN_VERSION = 1


def _build_parser() -> argparse.ArgumentParser:
    """Build the master-data CLI argument parser."""
    parser = argparse.ArgumentParser(
        description=(
            "Review and explicitly apply platform master data. "
            "The default command is a read-only preview."
        )
    )
    parser.set_defaults(command="preview")
    subparsers = parser.add_subparsers(dest="command")

    preview = subparsers.add_parser(
        "preview", help="Print a read-only plan containing source values."
    )
    preview.add_argument(
        "--domain",
        dest="domains",
        action="append",
        help="Limit the preview to one or more domain keys.",
    )
    preview.add_argument(
        "--format",
        choices=("json", "markdown", "text"),
        help=(
            "Output format. Defaults to Markdown on stdout and JSON when "
            "--output is supplied."
        ),
    )
    preview.add_argument(
        "--output", type=Path, help="Write the review plan to this file."
    )

    apply = subparsers.add_parser(
        "apply", help="Apply a previously generated review plan."
    )
    apply.add_argument(
        "--plan", type=Path, help="JSON plan file produced by the preview command."
    )
    apply.add_argument(
        "--reset",
        action="store_true",
        help="Restore source defaults; unavailable in production and requires --yes.",
    )
    apply.add_argument(
        "--yes",
        action="store_true",
        help="Confirm the destructive reset behavior in non-production environments.",
    )
    return parser


def _selected_previews(
    previews: list[dict[str, Any]], domains: Sequence[str] | None
) -> list[dict[str, Any]]:
    """Select requested domains and reject unknown source definitions."""
    if not domains:
        return previews

    by_key = {preview["key"]: preview for preview in previews}
    unknown = sorted(set(domains) - set(by_key))
    if unknown:
        raise ValueError(f"Unknown master-data domain(s): {', '.join(unknown)}")
    return [by_key[domain] for domain in domains]


def _plan_payload(previews: list[dict[str, Any]]) -> dict[str, Any]:
    """Build a portable review plan from source previews."""
    return {
        "plan_version": PLAN_VERSION,
        "definition_version": SEED_DEFINITION_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "domains": [preview["key"] for preview in previews if preview["seedable"]],
        "definition_hashes": {
            preview["key"]: preview["definition_hash"] for preview in previews
        },
        "catalog": previews,
    }


def _render_text(plan: dict[str, Any]) -> str:
    """Render a compact human-readable summary while retaining full JSON output."""
    lines = [
        f"Master-data definition version: {plan['definition_version']}",
        f"Generated at: {plan['generated_at']}",
        "",
    ]
    for domain in plan["catalog"]:
        lines.extend(
            [
                f"[{domain['key']}] {domain['display_name']}",
                f"  status={domain['status']} seedable={domain['seedable']} "
                f"expected={domain['expected_count']} current={domain['current_count']}",
                f"  source={domain['source']}",
                f"  definition_hash={domain['definition_hash']}",
                f"  items={len(domain['items'])}",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def _markdown_cell(value: Any) -> str:
    """Format a value safely for a Markdown table cell."""
    if value is None or value == "":
        return "—"
    return str(value).replace("|", "\\|").replace("\n", "<br>")


def _markdown_fence(content: Any, language: str = "text") -> list[str]:
    """Wrap arbitrary content in a Markdown fence that cannot close early."""
    text = "" if content is None else str(content).replace("\r\n", "\n")
    longest_run = max(
        (len(match) for match in re.findall(r"`+", text)),
        default=0,
    )
    fence = "`" * max(3, longest_run + 1)
    return [f"{fence}{language}", text.rstrip("\n"), fence]


def _append_catalog_items(lines: list[str], domain: dict[str, Any]) -> None:
    """Append the concise catalog-item index for one domain."""
    items = domain.get("items") or []
    lines.extend(["### Catalog items", ""])
    if not items:
        lines.extend(["No catalog items are defined in the source.", ""])
        return
    lines.extend(
        [
            "| Key | Label | Description |",
            "| --- | --- | --- |",
        ]
    )
    for item in items:
        lines.append(
            "| "
            + " | ".join(
                _markdown_cell(item.get(field))
                for field in ("key", "label", "description")
            )
            + " |"
        )
    lines.append("")


def _append_skill_payload(lines: list[str], payload: Any) -> None:
    """Append full skill instructions and reference-file contents."""
    lines.extend(["### Full skill contents", ""])
    if not isinstance(payload, list):
        lines.extend(
            _markdown_fence(json.dumps(payload, indent=2, default=str), "json")
        )
        lines.append("")
        return

    for index, skill in enumerate(payload, start=1):
        if not isinstance(skill, dict):
            lines.extend(_markdown_fence(skill, "text"))
            lines.append("")
            continue
        name = skill.get("name") or skill.get("slug") or f"Skill {index}"
        slug = skill.get("slug", "unknown")
        lines.extend(
            [
                "<details>",
                f"<summary><strong>{index}. {_markdown_cell(name)}</strong> "
                f"(<code>{_markdown_cell(slug)}</code>)</summary>",
                "",
                f"**Description:** {_markdown_cell(skill.get('description'))}",
                "",
                "#### Instructions",
                *_markdown_fence(skill.get("content"), "markdown"),
                "",
            ]
        )
        files = skill.get("files") or skill.get("default_files") or []
        if files:
            lines.extend(["#### Reference files", ""])
            for file_index, file_definition in enumerate(files, start=1):
                if not isinstance(file_definition, dict):
                    continue
                path = file_definition.get("file_path", f"file-{file_index}")
                lines.extend(
                    [
                        f"##### `{_markdown_cell(path)}`",
                        "",
                        *_markdown_fence(file_definition.get("content"), "markdown"),
                        "",
                    ]
                )
        lines.extend(["</details>", ""])


def _append_tool_payload(lines: list[str], payload: Any) -> None:
    """Append runtime-discovered tool names, functions, and schemas."""
    lines.extend(["### Tool schemas", ""])
    if not isinstance(payload, list):
        lines.extend(
            _markdown_fence(json.dumps(payload, indent=2, default=str), "json")
        )
        lines.append("")
        return
    for tool in payload:
        if not isinstance(tool, dict):
            continue
        lines.extend([f"#### `{_markdown_cell(tool.get('name'))}`", ""])
        functions = tool.get("functions") or []
        if not functions:
            lines.extend(["No function schemas were discovered.", ""])
            continue
        for function in functions:
            if not isinstance(function, dict):
                continue
            function_name = function.get("name") or function.get("function", "unknown")
            description = function.get("description")
            lines.append(f"- **Function:** `{_markdown_cell(function_name)}`")
            if description:
                lines.append(f"  **Description:** {_markdown_cell(description)}")
            schema = function.get("parameters") or function.get("schema")
            if schema:
                lines.extend(
                    [
                        "  **Parameters:**",
                        *_markdown_fence(
                            json.dumps(schema, indent=2, sort_keys=True, default=str),
                            "json",
                        ),
                    ]
                )
            lines.append("")


def _append_pricing_payload(lines: list[str], payload: Any) -> None:
    """Append usage-pricing activities and their default credit values."""
    lines.extend(["### Usage-pricing values", ""])
    if not isinstance(payload, list):
        lines.extend(
            _markdown_fence(json.dumps(payload, indent=2, default=str), "json")
        )
        lines.append("")
        return
    lines.extend(
        [
            "| Activity | Description | Default credits | Category | Meter | Unit |",
            "| --- | --- | ---: | --- | --- | --- |",
        ]
    )
    for item in payload:
        if not isinstance(item, dict):
            continue
        lines.append(
            "| "
            + " | ".join(
                _markdown_cell(
                    item.get(field)
                    if field != "credit_cost"
                    else item.get("default_credit_cost", item.get("credit_cost"))
                )
                for field in (
                    "event_name",
                    "description",
                    "credit_cost",
                    "category",
                    "meter_type",
                    "billing_unit",
                )
            )
            + " |"
        )
    lines.append("")


def _append_notification_payload(lines: list[str], payload: Any) -> None:
    """Append notification event keys, names, and template variables."""
    lines.extend(["### Notification-event values", ""])
    if not isinstance(payload, dict):
        lines.extend(
            _markdown_fence(json.dumps(payload, indent=2, default=str), "json")
        )
        lines.append("")
        return
    lines.extend(
        [
            "| Event key | Name | Template variables |",
            "| --- | --- | --- |",
        ]
    )
    for event_key, event in sorted(payload.items()):
        event = event if isinstance(event, dict) else {"name": event}
        variables = event.get("variables") or []
        variable_text = ", ".join(f"`{variable}`" for variable in variables) or "—"
        lines.append(
            f"| `{_markdown_cell(event_key)}` | "
            f"{_markdown_cell(event.get('name'))} | {variable_text} |"
        )
    lines.append("")


def _append_domain_payload(lines: list[str], domain: dict[str, Any]) -> None:
    """Append the most readable representation available for one source payload."""
    key = domain.get("key")
    payload = domain.get("payload")
    if key == "platform_skills":
        _append_skill_payload(lines, payload)
        return
    if key == "platform_tools":
        _append_tool_payload(lines, payload)
        return
    if key == "system_pricing":
        _append_pricing_payload(lines, payload)
        return
    if key == "notification_events":
        _append_notification_payload(lines, payload)
        return

    lines.extend(["### Source payload", ""])
    if isinstance(payload, str) and (
        payload.startswith("review-gated") or payload.startswith("migration-managed")
    ):
        lines.extend(
            [
                f"> No independent seed payload exists for this domain: `{payload}`.",
                "> Review the migration or launch decision referenced above instead.",
                "",
            ]
        )
        return
    lines.extend(
        _markdown_fence(
            json.dumps(payload, indent=2, sort_keys=True, default=str), "json"
        )
    )
    lines.append("")


def _render_markdown(plan: dict[str, Any]) -> str:
    """Render a navigable human-readable review report with full source values."""
    catalog = plan.get("catalog", [])
    storage_model = {
        "platform_skills": (
            "Repository skill templates and reference files",
            "`platform_skills`, `platform_skill_files`",
            "Explicit CLI seed; content-hash idempotent",
        ),
        "platform_tools": (
            "Runtime tool registry and function schemas",
            "`platform_tools`",
            "Explicit CLI schema synchronization",
        ),
        "system_pricing": (
            "`SYSTEM_PRICING` source tuple",
            "`credit_events`",
            "Explicit CLI seed; existing rates preserved",
        ),
        "notification_events": (
            "Notification template registry",
            "`notification_events`",
            "Explicit CLI seed; existing rows preserved",
        ),
        "plan_catalog": (
            "Migrations and review-gated plan catalog",
            "`plan_products`, `plan_versions`",
            "Migration/admin workflow; not seeded here",
        ),
        "credit_products": (
            "`CREDIT_PACKS` and Stripe manager",
            "`credit_products`",
            "Stripe manager preview/sync; excluded from generic apply",
        ),
    }

    lines = [
        "# Master-data review",
        "",
        "> Read-only review artifact. This report is generated from the checked-out "
        "source definitions and current database counts; it is not a write operation.",
        "",
        f"- **Definition version:** `{plan.get('definition_version', 'unknown')}`",
        f"- **Generated at:** `{plan.get('generated_at', 'unknown')}`",
        f"- **Seedable domains in this plan:** `{len(plan.get('domains', []))}`",
        "",
        "## How to use this report",
        "",
        "1. Start with **Storage model** to see where each value originates and "
        "which database table receives it.",
        "2. Use **At a glance** to identify pending, seeded, review-gated, and "
        "migration-managed domains.",
        "3. Open the domain sections below. Platform skills include their complete "
        "instructions and reference files; pricing, tools, and notifications are "
        "shown as readable tables.",
        "4. Apply only the JSON plan after this report has been reviewed. The Markdown "
        "file itself is a reviewable artifact, not a source of truth.",
        "",
        "## Storage model",
        "",
        "Master data has three layers:",
        "",
        "- **Source definitions:** version-controlled Python modules and Alembic migrations.",
        "- **Materialized database rows:** the runtime tables used by the application.",
        "- **Review artifacts:** generated JSON/Markdown files; these are temporary "
        "operator evidence and are not loaded automatically at startup.",
        "",
        "| Domain | Source of truth | Materialized database storage | Seed behavior |",
        "| --- | --- | --- | --- |",
    ]
    for domain in catalog:
        source, database, behavior = storage_model.get(
            domain.get("key"),
            (
                domain.get("source", "Repository source"),
                "See migration/schema",
                "Inventory only",
            ),
        )
        lines.append(
            f"| `{_markdown_cell(domain.get('key'))}` | {source} | {database} | {behavior} |"
        )
    lines.extend(["", "## At a glance", ""])
    lines.extend(
        [
            "| # | Domain | Status | Seedable | Expected | Current |",
            "| ---: | --- | --- | :---: | ---: | ---: |",
        ]
    )
    for index, domain in enumerate(catalog, start=1):
        lines.append(
            f"| {index} | `{_markdown_cell(domain.get('key'))}` — "
            f"{_markdown_cell(domain.get('display_name'))} | "
            f"{_markdown_cell(domain.get('status'))} | "
            f"{'Yes' if domain.get('seedable') else 'No'} | "
            f"{_markdown_cell(domain.get('expected_count'))} | "
            f"{_markdown_cell(domain.get('current_count'))} |"
        )

    for index, domain in enumerate(catalog, start=1):
        lines.extend(
            [
                "",
                f"## {index}. {_markdown_cell(domain.get('display_name'))}",
                "",
                f"- **Domain key:** `{_markdown_cell(domain.get('key'))}`",
                f"- **Category:** {_markdown_cell(domain.get('category'))}",
                f"- **Source path:** `{_markdown_cell(domain.get('source'))}`",
                f"- **Definition hash:** `{_markdown_cell(domain.get('definition_hash'))}`",
                f"- **Policy:** {'Seedable by explicit CLI apply' if domain.get('seedable') else 'Not seedable by this CLI'}",
                f"- **Description:** {_markdown_cell(domain.get('description'))}",
                "",
            ]
        )
        _append_catalog_items(lines, domain)
        _append_domain_payload(lines, domain)
    return "\n".join(lines).rstrip() + "\n"


def _write_preview(
    plan: dict[str, Any], output: Path | None, output_format: Optional[str]
) -> None:
    """Write the read-only plan to stdout or an operator-selected file."""
    resolved_format = output_format or ("json" if output else "markdown")
    if output and resolved_format == "text":
        raise ValueError("Use JSON format when writing a plan file for apply")
    if resolved_format == "text":
        rendered = _render_text(plan)
    elif resolved_format == "markdown":
        rendered = _render_markdown(plan)
    else:
        rendered = json.dumps(plan, indent=2, sort_keys=True, default=str) + "\n"

    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
        artifact = "review report" if resolved_format == "markdown" else "plan"
        print(f"Wrote read-only master-data {artifact} to {output}")
    else:
        print(rendered, end="")


async def _preview(args: argparse.Namespace) -> int:
    """Generate a read-only plan containing all requested source values."""
    service = MasterDataService()
    previews = _selected_previews(
        await service.preview(), getattr(args, "domains", None)
    )
    _write_preview(
        _plan_payload(previews),
        getattr(args, "output", None),
        getattr(args, "format", None),
    )
    return 0


def _production_reset_requested(args: argparse.Namespace) -> bool:
    """Return whether a reset was requested against a production environment."""
    environment = os.getenv("ENVIRONMENT", "").strip().lower()
    return args.reset and environment in {"prod", "production"}


def _reset_environment_is_allowed(args: argparse.Namespace) -> bool:
    """Return whether reset is running in an explicitly allowed environment."""
    environment = os.getenv("ENVIRONMENT", "").strip().lower()
    return not args.reset or environment in RESET_ALLOWED_ENVIRONMENTS


async def _apply(args: argparse.Namespace) -> int:
    """Apply a reviewed plan after validating source hashes and safety flags."""
    if _production_reset_requested(args):
        print(
            "Master-data reset is not supported in production; create a "
            "forward-only data change instead.",
            file=sys.stderr,
        )
        return 2
    if not _reset_environment_is_allowed(args):
        print(
            "Reset requires an explicit non-production ENVIRONMENT "
            "(development, test, local, or staging).",
            file=sys.stderr,
        )
        return 2
    if args.reset and not args.yes:
        print("Reset requires explicit --yes confirmation.", file=sys.stderr)
        return 2
    if not args.plan:
        print("Apply requires --plan from a prior read-only preview.", file=sys.stderr)
        return 2

    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    if not isinstance(plan, dict):
        raise ValueError("Master-data plan must be a JSON object")
    if plan.get("plan_version") != PLAN_VERSION:
        raise ValueError("Unsupported master-data plan version")
    if plan.get("definition_version") != SEED_DEFINITION_VERSION:
        raise ValueError("Unsupported master-data definition version")

    raw_domains = plan.get("domains")
    if not isinstance(raw_domains, list) or not all(
        isinstance(domain, str) for domain in raw_domains
    ):
        raise ValueError("Master-data plan domains must be a list of strings")
    domains = list(raw_domains)
    if len(set(domains)) != len(domains):
        raise ValueError("Master-data plan contains duplicate domains")
    if not domains:
        print(
            "The review plan contains no seedable domains; nothing was applied.",
            file=sys.stderr,
        )
        return 2
    definition_hashes = plan.get("definition_hashes")
    if not isinstance(definition_hashes, dict):
        raise ValueError("Master-data plan definition_hashes must be an object")
    missing_hashes = [
        domain
        for domain in domains
        if not isinstance(definition_hashes.get(domain), str)
    ]
    if missing_hashes:
        raise ValueError(
            "Master-data plan is missing definition hashes for: "
            + ", ".join(sorted(missing_hashes))
        )
    raw_catalog = plan.get("catalog")
    if not isinstance(raw_catalog, list) or not all(
        isinstance(entry, dict) and isinstance(entry.get("key"), str)
        for entry in raw_catalog
    ):
        raise ValueError("Master-data plan must contain a catalog entry for review")
    catalog_keys = [entry["key"] for entry in raw_catalog]
    if len(set(catalog_keys)) != len(catalog_keys):
        raise ValueError("Master-data plan catalog contains duplicate entries")
    catalog_by_key = {entry["key"]: entry for entry in raw_catalog}
    missing_catalog = sorted(set(domains) - set(catalog_by_key))
    if missing_catalog:
        raise ValueError(
            "Master-data plan is missing a catalog entry for: "
            + ", ".join(missing_catalog)
        )
    service = MasterDataService()
    current_previews = await service.preview()
    current_by_key = {preview["key"]: preview for preview in current_previews}
    missing = sorted(set(domains) - set(current_by_key))
    changed = sorted(
        domain
        for domain in domains
        if domain not in current_by_key
        or definition_hashes.get(domain) != current_by_key[domain]["definition_hash"]
    )
    if missing:
        raise ValueError(f"Unknown master-data domain(s): {', '.join(missing)}")
    if changed:
        raise ValueError(
            "Source definition changed since preview for: " + ", ".join(changed)
        )
    modified_catalog = sorted(
        domain
        for domain in domains
        if catalog_by_key[domain].get("seedable") is not True
        or catalog_by_key[domain].get("definition_version")
        != current_by_key[domain].get("definition_version")
        or catalog_by_key[domain].get("definition_hash")
        != current_by_key[domain].get("definition_hash")
        or catalog_by_key[domain].get("payload")
        != current_by_key[domain].get("payload")
    )
    if modified_catalog:
        raise ValueError(
            "The reviewed catalog differs from the current source for: "
            + ", ".join(modified_catalog)
        )

    results = await service.seed_domains(
        domains,
        triggered_by=None,
        reset=args.reset,
        expected_definition_hashes=definition_hashes,
    )
    print(json.dumps({"results": results}, indent=2, sort_keys=True, default=str))
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Run the dry-run-first master-data CLI and return a process exit code."""
    args = _build_parser().parse_args(argv)
    try:
        if args.command == "apply":
            return asyncio.run(_apply(args))
        return asyncio.run(_preview(args))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Master-data command failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
