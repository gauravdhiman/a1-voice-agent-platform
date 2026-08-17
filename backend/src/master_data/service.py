"""Audited, idempotent, explicitly invoked master-data seeding service."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID, uuid4

from shared.config import supabase_config

from .definitions import (
    SEED_DEFINITION_VERSION,
    MasterDataDefinition,
    build_master_data_catalog,
)

logger = logging.getLogger(__name__)

RESET_ALLOWED_ENVIRONMENTS = frozenset(
    {"development", "dev", "local", "test", "staging"}
)


class MasterDataService:
    """Review and seed platform-owned data through an explicit operator command.

    Migration-managed and review-gated domains are intentionally read-only in
    this service. The CLI invokes ``preview`` first, then passes the reviewed
    source hashes to ``seed_domains`` so stale plans cannot silently replace
    approved pricing, plan versions, or user-facing catalog edits.
    """

    def __init__(self, supabase_client: Any = None) -> None:
        """Initialize the service with an optional database client for tests."""
        self.supabase = supabase_client or supabase_config.service_client
        from shared.voice_agents.tools.base.platform_tool_registry import (
            platform_tool_registry,
        )

        self.tool_registry = platform_tool_registry

    def _seedable_domain_keys(self) -> tuple[str, ...]:
        """Return seedable domains after runtime tool discovery is complete."""
        return tuple(
            definition.key for definition in self._catalog() if definition.seedable
        )

    def _ensure_tools_registered(self) -> None:
        """Discover in-tree tools before generating a preview or seeding them."""
        if not self.tool_registry.get_tool_names():
            self.tool_registry.register_tools_from_package(
                "shared.voice_agents.tools.implementations"
            )

    def _catalog(self) -> tuple[MasterDataDefinition, ...]:
        """Return the current source catalog with runtime tool discovery applied."""
        self._ensure_tools_registered()
        tool_names = self.tool_registry.get_tool_names()
        tool_details = []
        for name in tool_names:
            schemas = []
            for function in self.tool_registry.get_tool_functions(name):
                schema = self.tool_registry._extract_schema_from_function(function)
                if schema:
                    schemas.append(schema)
            tool_details.append({"name": name, "functions": schemas})
        return build_master_data_catalog(tool_names, tool_details)

    async def preview(self) -> list[dict[str, Any]]:
        """Return source definitions, current counts, and seed-run status."""
        previews: list[dict[str, Any]] = []
        for definition in self._catalog():
            current_count = await self._safe_current_count(definition)
            last_run = await self._get_last_completed_run(definition.key)
            if definition.requires_review:
                seed_status = "review_required"
            elif definition.migration_managed:
                seed_status = "migration_managed"
            elif last_run is None:
                seed_status = "pending"
            elif last_run.get("definition_hash") == definition.definition_hash:
                seed_status = "seeded"
            else:
                seed_status = "source_changed"

            previews.append(
                {
                    "key": definition.key,
                    "display_name": definition.display_name,
                    "category": definition.category,
                    "description": definition.description,
                    "source": definition.source,
                    "definition_version": SEED_DEFINITION_VERSION,
                    "definition_hash": definition.definition_hash,
                    "expected_count": definition.expected_count,
                    "current_count": current_count,
                    "seedable": definition.seedable,
                    "requires_review": definition.requires_review,
                    "migration_managed": definition.migration_managed,
                    "status": seed_status,
                    "items": [
                        {"key": key, "label": label, "description": description}
                        for key, label, description in definition.items
                    ],
                    "payload": definition.payload,
                    "last_run": last_run,
                }
            )
        return previews

    async def seed_domains(
        self,
        domains: list[str],
        *,
        triggered_by: Optional[UUID | str],
        reset: bool = False,
        expected_definition_hashes: Optional[dict[str, str]] = None,
    ) -> list[dict[str, Any]]:
        """Explicitly seed approved domains and write an audit record.

        Args:
            domains: Domain keys from the preview. An empty list means all
                currently seedable domains.
            triggered_by: Platform-admin user ID, or ``None`` for CLI execution.
            reset: Reapply source defaults where the provider supports it.
            expected_definition_hashes: Hashes captured by a reviewed CLI plan.
                When supplied, the source catalog must still match before any
                provider writes begin.

        Raises:
            ValueError: If a domain is unknown, migration-managed, or requires
                business review before it can be seeded.
        RuntimeError: If the provider or seed ledger cannot complete.
        """
        if (
            reset
            and os.getenv("ENVIRONMENT", "").strip().lower()
            not in RESET_ALLOWED_ENVIRONMENTS
        ):
            raise ValueError(
                "Reset requires an explicit non-production ENVIRONMENT "
                "(development, test, local, or staging)."
            )
        catalog_by_key = {definition.key: definition for definition in self._catalog()}
        requested = domains or list(self._seedable_domain_keys())
        if len(set(requested)) != len(requested):
            raise ValueError("Master-data seed request contains duplicate domains")
        self._validate_requested_domains(requested, catalog_by_key)
        if expected_definition_hashes is not None:
            missing_hashes = [
                domain
                for domain in requested
                if not isinstance(expected_definition_hashes.get(domain), str)
            ]
            if missing_hashes:
                raise ValueError(
                    "Reviewed plan is missing definition hashes for: "
                    + ", ".join(sorted(missing_hashes))
                )
            changed = [
                domain
                for domain in requested
                if expected_definition_hashes.get(domain)
                != catalog_by_key[domain].definition_hash
            ]
            if changed:
                raise ValueError(
                    "Source definition changed since preview for: "
                    + ", ".join(sorted(changed))
                )
        results: list[dict[str, Any]] = []

        for domain in requested:
            definition = catalog_by_key[domain]
            operation = "reset" if reset else "seed"
            run_id = uuid4()
            await self._record_seed_run(
                run_id,
                definition,
                operation=operation,
                status="running",
                triggered_by=triggered_by,
                details={},
            )
            try:
                details = await self._seed_domain(domain, reset=reset)
                result = {
                    "domain": domain,
                    "operation": operation,
                    "changed": int(details.get("changed", 0)),
                    "details": details,
                }
                await self._record_seed_run(
                    run_id,
                    definition,
                    operation=operation,
                    status="completed",
                    triggered_by=triggered_by,
                    details=details,
                )
                results.append(result)
            except Exception as exc:
                await self._record_seed_run(
                    run_id,
                    definition,
                    operation=operation,
                    status="failed",
                    triggered_by=triggered_by,
                    details={},
                    error_message=str(exc),
                )
                logger.error("Master-data seed failed for %s", domain, exc_info=True)
                raise
        return results

    @staticmethod
    def _validate_requested_domains(
        requested: list[str], catalog_by_key: dict[str, MasterDataDefinition]
    ) -> None:
        """Reject domains that are not safe for this provider."""
        unknown = sorted(set(requested) - set(catalog_by_key))
        if unknown:
            raise ValueError(f"Unknown master-data domain(s): {', '.join(unknown)}")
        blocked = [key for key in requested if not catalog_by_key[key].seedable]
        if blocked:
            raise ValueError(
                "These domains are migration-managed or review-gated and cannot "
                f"be seeded by this action: {', '.join(blocked)}"
            )

    async def _seed_domain(self, domain: str, *, reset: bool = False) -> dict[str, Any]:
        """Dispatch one approved domain to its existing source-of-truth provider."""
        if domain == "platform_skills":
            from shared.voice_agents.skill_service import skill_service

            changed, error = await skill_service.seed_platform_skills(
                prune_orphans=reset
            )
            if error:
                raise RuntimeError(error)
            return {"changed": changed}

        if domain == "platform_tools":
            from shared.voice_agents.tool_service import ToolService

            self._ensure_tools_registered()
            await self.tool_registry.sync_with_db(ToolService())
            return {"changed": len(self.tool_registry.get_tool_names())}

        if domain == "system_pricing":
            return await self._seed_system_pricing(reset=reset)

        if domain == "notification_events":
            return await self._seed_notification_events(reset=reset)

        raise ValueError(f"No provider registered for master-data domain '{domain}'")

    async def _seed_system_pricing(self, *, reset: bool) -> dict[str, Any]:
        """Create missing usage prices and optionally restore source defaults."""
        from src.billing.system_pricing import SYSTEM_PRICING

        table = self.supabase.table("credit_events")
        existing_rows = (
            table.select(
                "name, description, credit_cost, category, is_active, "
                "meter_type, billing_unit"
            )
            .in_("name", [item.event_name for item in SYSTEM_PRICING])
            .execute()
        ).data or []
        existing_by_name = {row["name"]: row for row in existing_rows}
        rows: list[dict[str, Any]] = []
        for item in SYSTEM_PRICING:
            existing = existing_by_name.get(item.event_name)
            default_row = {
                "name": item.event_name,
                "description": item.description,
                "credit_cost": item.default_credit_cost,
                "category": item.category,
                "is_active": True,
                "meter_type": item.meter_type,
                "billing_unit": item.billing_unit,
            }
            if existing is not None and not reset:
                default_row["credit_cost"] = existing.get(
                    "credit_cost", item.default_credit_cost
                )
                default_row["is_active"] = existing.get("is_active", True)

            if existing is None or any(
                existing.get(field) != value
                for field, value in default_row.items()
                if field != "name"
            ):
                rows.append(default_row)

        if rows:
            table.upsert(rows, on_conflict="name").execute()
        return {"changed": len(rows), "reset_defaults": reset}

    async def _seed_notification_events(self, *, reset: bool) -> dict[str, Any]:
        """Create missing events and restore built-in metadata when requested."""
        from src.notifications.models import (
            NotificationCategory,
            NotificationEventCreate,
            NotificationEventUpdate,
        )
        from src.notifications.service import notification_service
        from src.notifications.templates import TEMPLATE_REGISTRY

        categories = {
            "user.signup": NotificationCategory.AUTH,
            "user.password_reset": NotificationCategory.AUTH,
            "user.email_verification": NotificationCategory.AUTH,
            "subscription.created": NotificationCategory.BILLING,
            "subscription.cancelled": NotificationCategory.BILLING,
            "credits.low_balance": NotificationCategory.BILLING,
            "credits.purchased": NotificationCategory.BILLING,
            "organization.invitation": NotificationCategory.ORGANIZATION,
            "billing.payment_failed": NotificationCategory.BILLING,
            "tools.oauth_reauthorization_required": NotificationCategory.AUTH,
        }
        changed = 0
        for event_key, template_data in TEMPLATE_REGISTRY.items():
            existing_event = await notification_service.get_notification_event_by_key(
                event_key
            )
            category = categories.get(event_key, NotificationCategory.CUSTOM)
            metadata = {
                "built_in_template": True,
                "variables": template_data.get("variables", []),
            }
            if existing_event and reset:
                await notification_service.update_notification_event(
                    existing_event.id,
                    NotificationEventUpdate(
                        name=template_data["name"],
                        description=f"Notification event for {template_data['name']}",
                        category=category,
                        is_enabled=True,
                        metadata=metadata,
                    ),
                )
                changed += 1
                continue
            if existing_event:
                continue
            await notification_service.create_notification_event(
                NotificationEventCreate(
                    name=template_data["name"],
                    description=f"Notification event for {template_data['name']}",
                    event_key=event_key,
                    category=category,
                    is_enabled=True,
                    metadata=metadata,
                )
            )
            changed += 1
        return {"changed": changed}

    async def _safe_current_count(
        self, definition: MasterDataDefinition
    ) -> Optional[int]:
        """Return a current row count, or ``None`` if the table is unavailable."""
        table_name = {
            "platform_skills": "platform_skills",
            "platform_tools": "platform_tools",
            "system_pricing": "credit_events",
            "notification_events": "notification_events",
            "plan_catalog": "plan_products",
            "credit_products": "credit_products",
            "entitlement_definitions": "entitlement_definitions",
            "voice_templates": "voice_templates",
            "pipeline_presets": "pipeline_presets",
        }.get(definition.key)
        if not table_name or self.supabase is None:
            return None
        try:
            count_column = (
                "key" if definition.key == "entitlement_definitions" else "id"
            )
            query = self.supabase.table(table_name).select(count_column)
            if definition.key == "platform_tools":
                query = query.eq("tool_source", "legacy")
            elif definition.key == "system_pricing":
                from src.billing.system_pricing import SYSTEM_PRICING_EVENT_NAMES

                query = query.in_("name", list(SYSTEM_PRICING_EVENT_NAMES))
            elif definition.key == "notification_events":
                from src.notifications.templates import TEMPLATE_REGISTRY

                query = query.in_("event_key", list(TEMPLATE_REGISTRY))
            return len(query.execute().data or [])
        except Exception:
            logger.warning("Unable to count master-data domain %s", definition.key)
            return None

    async def _get_last_completed_run(self, domain: str) -> Optional[dict[str, Any]]:
        """Return the latest successful run for one domain."""
        if self.supabase is None:
            raise RuntimeError("Supabase is not configured")
        result = (
            self.supabase.table("master_data_seed_runs")
            .select("*")
            .eq("domain", domain)
            .eq("status", "completed")
            .order("completed_at", desc=True)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None

    async def _record_seed_run(
        self,
        run_id: UUID,
        definition: MasterDataDefinition,
        *,
        operation: str,
        status: str,
        triggered_by: Optional[UUID | str],
        details: dict[str, Any],
        error_message: Optional[str] = None,
    ) -> None:
        """Insert or update one audit ledger row."""
        if self.supabase is None:
            raise RuntimeError("Supabase is not configured")
        row = {
            "domain": definition.key,
            "definition_version": SEED_DEFINITION_VERSION,
            "definition_hash": definition.definition_hash,
            "operation": operation,
            "status": status,
            "triggered_by": str(triggered_by) if triggered_by else None,
            "details": details,
            "error_message": error_message,
        }
        if status == "running":
            row["id"] = str(run_id)
            self.supabase.table("master_data_seed_runs").insert(row).execute()
            return
        row["completed_at"] = datetime.now(timezone.utc).isoformat()
        self.supabase.table("master_data_seed_runs").update(row).eq(
            "id", str(run_id)
        ).execute()


master_data_service = MasterDataService()
