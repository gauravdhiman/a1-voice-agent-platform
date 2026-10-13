"""Canonical master-data definitions used by CLI review and seed workflows.

This module is deliberately a catalog, not a second copy of the underlying
records. Code-backed domains derive their hashes from the existing source of
truth; migration-backed and commercially undecided domains are listed so an
operator can see their ownership and status before taking action.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any, Optional

SEED_DEFINITION_VERSION = "2026.08.13.1"


@dataclass(frozen=True)
class MasterDataDefinition:
    """Describe one master-data domain without performing database writes."""

    key: str
    display_name: str
    category: str
    description: str
    source: str
    expected_count: Optional[int]
    seedable: bool
    requires_review: bool
    migration_managed: bool
    items: tuple[tuple[str, str, Optional[str]], ...]
    payload: Any

    @property
    def definition_hash(self) -> str:
        """Return a stable hash of the source definition."""
        encoded = json.dumps(self.payload, sort_keys=True, default=str).encode()
        return hashlib.sha256(encoded).hexdigest()


def _items(
    rows: list[tuple[str, str, Optional[str]]]
) -> tuple[tuple[str, str, Optional[str]], ...]:
    """Convert a mutable item list into an immutable catalog representation."""
    return tuple(rows)


def build_master_data_catalog(
    tool_names: Optional[list[str]] = None,
    tool_details: Optional[list[dict[str, Any]]] = None,
) -> tuple[MasterDataDefinition, ...]:
    """Build the complete operator-facing master-data catalog.

    Args:
        tool_names: Registered platform tools, supplied by the runtime after
            discovery. An empty list is valid when optional tool imports fail.
        tool_details: Optional schema payloads for the registered tools. When
            supplied, these are hashed so function-contract changes are visible
            in the review screen.

    Returns:
        A tuple containing code-backed, migration-backed, and review-gated
        domains in a stable order for CLI plans and review artifacts.
    """
    from src.billing.credit_catalog import CREDIT_PACKS
    from src.billing.system_pricing import SYSTEM_PRICING
    from src.legal.content import (
        PRIVACY_V1_MARKDOWN,
        PRIVACY_V1_SUMMARY,
        TERMS_V1_MARKDOWN,
        TERMS_V1_SUMMARY,
    )
    from src.notifications.templates import TEMPLATE_REGISTRY
    from src.voice_agents.skill_seeds import PLATFORM_SKILL_TEMPLATES

    tools = sorted(tool_names or [])
    skill_items = [
        (seed["slug"], seed["name"], seed.get("description"))
        for seed in PLATFORM_SKILL_TEMPLATES
    ]
    pricing_items = [
        (item.event_name, item.display_name, item.description)
        for item in SYSTEM_PRICING
    ]
    notification_items = [
        (
            key,
            value["name"],
            f"Built-in template with {len(value.get('variables', []))} variables",
        )
        for key, value in sorted(TEMPLATE_REGISTRY.items())
    ]
    credit_pack_items = [
        (
            str(pack["credit_amount"]),
            pack["name"],
            f"${pack['price_usd']:.2f}",
        )
        for pack in CREDIT_PACKS
    ]
    legal_documents_payload = [
        {
            "document_key": "terms",
            "content_markdown": TERMS_V1_MARKDOWN,
            "summary_of_changes": TERMS_V1_SUMMARY,
        },
        {
            "document_key": "privacy",
            "content_markdown": PRIVACY_V1_MARKDOWN,
            "summary_of_changes": PRIVACY_V1_SUMMARY,
        },
    ]
    legal_document_items = [
        ("terms", "Terms & Conditions", TERMS_V1_SUMMARY),
        ("privacy", "Privacy Policy", PRIVACY_V1_SUMMARY),
    ]

    return (
        MasterDataDefinition(
            key="platform_skills",
            display_name="Platform skill templates",
            category="product",
            description="Industry-specific skills that organizations can fork for agents.",
            source="backend/src/voice_agents/skill_seeds.py",
            expected_count=len(skill_items),
            seedable=True,
            requires_review=False,
            migration_managed=False,
            items=_items(skill_items),
            payload=[
                {
                    "slug": seed["slug"],
                    "name": seed["name"],
                    "description": seed.get("description"),
                    "content": seed["content"],
                    "files": seed.get("default_files", []),
                }
                for seed in PLATFORM_SKILL_TEMPLATES
            ],
        ),
        MasterDataDefinition(
            key="platform_tools",
            display_name="Platform tool schemas",
            category="product",
            description="Runtime-discovered tools and function schemas exposed to agents.",
            source="shared/voice_agents/tools/implementations",
            expected_count=len(tools),
            seedable=True,
            requires_review=False,
            migration_managed=False,
            items=_items([(name, name, None) for name in tools]),
            payload=tool_details if tool_details is not None else tools,
        ),
        MasterDataDefinition(
            key="system_pricing",
            display_name="System usage pricing",
            category="billing",
            description="The finite set of runtime-metered activities and their source credit defaults.",
            source="backend/src/billing/system_pricing.py",
            expected_count=len(pricing_items),
            seedable=True,
            requires_review=False,
            migration_managed=False,
            items=_items(pricing_items),
            payload=[asdict(item) for item in SYSTEM_PRICING],
        ),
        MasterDataDefinition(
            key="notification_events",
            display_name="Notification events",
            category="operations",
            description="Built-in event keys used to connect platform activity to email templates.",
            source="backend/src/notifications/templates.py",
            expected_count=len(notification_items),
            seedable=True,
            requires_review=False,
            migration_managed=False,
            items=_items(notification_items),
            payload={
                key: {"name": value["name"], "variables": value.get("variables", [])}
                for key, value in sorted(TEMPLATE_REGISTRY.items())
            },
        ),
        MasterDataDefinition(
            key="legal_documents",
            display_name="Legal documents (initial published versions)",
            category="operations",
            description=(
                "Initial published Terms & Conditions and Privacy Policy content. "
                "Later versions are managed by platform admins through the Legal "
                "Documents UI."
            ),
            source="backend/src/legal/content.py",
            expected_count=len(legal_document_items),
            seedable=True,
            requires_review=False,
            migration_managed=False,
            items=_items(legal_document_items),
            payload=legal_documents_payload,
        ),
        MasterDataDefinition(
            key="plan_catalog",
            display_name="Plans and prices",
            category="billing",
            description="Free-plan defaults are migration-managed; paid launch plans remain review-gated until cost and market decisions are approved.",
            source="billing migrations plus platform plan catalog",
            expected_count=1,
            seedable=False,
            requires_review=True,
            migration_managed=True,
            items=_items(
                [
                    ("free", "Free plan", "Migration-managed starter plan"),
                    (
                        "paid-launch-plans",
                        "Paid launch plans",
                        "Requires approved pricing and margin assumptions",
                    ),
                ]
            ),
            payload="review-gated-plan-catalog",
        ),
        MasterDataDefinition(
            key="credit_products",
            display_name="Credit top-up products",
            category="billing",
            description=(
                "Code-owned credit packs are synchronized to Stripe by the Stripe "
                "manager; this domain is excluded from generic master-data apply."
            ),
            source="backend/src/billing/credit_catalog.py and backend/scripts/stripe_manager.py",
            expected_count=len(credit_pack_items),
            seedable=False,
            requires_review=True,
            migration_managed=False,
            items=_items(credit_pack_items),
            payload=[dict(pack) for pack in CREDIT_PACKS],
        ),
        MasterDataDefinition(
            key="entitlement_definitions",
            display_name="Plan entitlements",
            category="billing",
            description="Plan limit and feature keys required by runtime enforcement.",
            source="backend/alembic/versions/20260807000002_add_plan_versioning_and_entitlements.py",
            expected_count=11,
            seedable=False,
            requires_review=False,
            migration_managed=True,
            items=_items(
                [
                    (key, key.replace("_", " ").title(), None)
                    for key in (
                        "max_agents",
                        "max_org_members",
                        "max_phone_numbers",
                        "max_concurrent_calls",
                        "included_credits_per_billing_period",
                        "payg_credit_cap",
                        "payg_enabled",
                        "credit_topup_enabled",
                        "premium_tools",
                        "embed_widget",
                        "custom_branding",
                    )
                ]
            ),
            payload="migration-managed-entitlement-catalog-v2",
        ),
        MasterDataDefinition(
            key="voice_templates",
            display_name="Onboarding voice templates",
            category="product",
            description="Starter agent templates inserted by the onboarding migration.",
            source="backend/alembic/versions/20260329000001_add_onboarding_and_voice_templates.py",
            expected_count=5,
            seedable=False,
            requires_review=False,
            migration_managed=True,
            items=_items(
                [
                    ("dental-receptionist", "Dental Receptionist", "dental"),
                    ("hvac-service-dispatcher", "HVAC Service Dispatcher", "hvac"),
                    ("salon-spa-coordinator", "Salon & Spa Coordinator", "salon"),
                    ("real-estate-assistant", "Real Estate Assistant", "real_estate"),
                    (
                        "plumbing-service-scheduler",
                        "Plumbing Service Scheduler",
                        "plumbing",
                    ),
                ]
            ),
            payload="migration-managed-voice-template-catalog-v1",
        ),
        MasterDataDefinition(
            key="pipeline_presets",
            display_name="Voice pipeline presets",
            category="product",
            description="System-default realtime pipeline preset inserted by migration.",
            source="backend/alembic/versions/20260729000002_add_pipeline_presets_is_default.py",
            expected_count=1,
            seedable=False,
            requires_review=False,
            migration_managed=True,
            items=_items([("system-default", "System Default", "realtime")]),
            payload="migration-managed-pipeline-preset-v1",
        ),
        MasterDataDefinition(
            key="rbac_catalog",
            display_name="Roles and permissions",
            category="security",
            description="System roles and permissions required for platform and organization administration.",
            source="backend/alembic/versions/91759229c32b_add_initial_rbac_tables.py",
            expected_count=None,
            seedable=False,
            requires_review=False,
            migration_managed=True,
            items=_items([]),
            payload="migration-managed-rbac-catalog-v1",
        ),
        MasterDataDefinition(
            key="platform_settings",
            display_name="Platform singleton settings",
            category="operations",
            description="Singleton settings for phone-number lifecycle and platform notifications.",
            source="platform settings migrations",
            expected_count=2,
            seedable=False,
            requires_review=False,
            migration_managed=True,
            items=_items(
                [
                    ("phone-number-settings", "Phone-number settings", None),
                    ("notification-settings", "Notification settings", None),
                ]
            ),
            payload="migration-managed-platform-settings-v1",
        ),
    )
