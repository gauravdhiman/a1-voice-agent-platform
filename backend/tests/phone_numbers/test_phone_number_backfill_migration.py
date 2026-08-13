"""Tests for the legacy voice-agent phone-number data migration."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

MIGRATION_PATH = (
    Path(__file__).parents[2]
    / "alembic"
    / "versions"
    / "20260812000006_backfill_phone_numbers_from_voice_agents.py"
)
SPEC = spec_from_file_location("phone_number_backfill_migration", MIGRATION_PATH)
assert SPEC and SPEC.loader
MIGRATION = module_from_spec(SPEC)
SPEC.loader.exec_module(MIGRATION)


def test_normalize_legacy_phone_accepts_common_us_formatting() -> None:
    """Historical US formatting is converted to the canonical E.164 value."""
    assert MIGRATION.normalize_legacy_phone("(415) 555-0100") == "+14155550100"
    assert MIGRATION.normalize_legacy_phone("415.555.0100") == "+14155550100"


def test_normalize_legacy_phone_preserves_international_e164() -> None:
    """International values that already include a plus sign are preserved."""
    assert MIGRATION.normalize_legacy_phone(" +44 1632 960000 ") == "+441632960000"


@pytest.mark.parametrize("value", ["", "415555", "0014155550100", "abc"])
def test_normalize_legacy_phone_rejects_ambiguous_values(value: str) -> None:
    """The deployment must stop rather than guess an unsafe phone mapping."""
    with pytest.raises(ValueError):
        MIGRATION.normalize_legacy_phone(value)


def test_build_backfill_plan_is_idempotent_for_existing_assignment() -> None:
    """A rerun produces no insert/update after the row is already assigned."""
    legacy = [
        {
            "organization_id": "org-1",
            "agent_id": "agent-1",
            "phone_number": "+1 (415) 555-0100",
            "is_active": True,
            "created_at": None,
        }
    ]
    existing = [
        {
            "id": "phone-1",
            "organization_id": "org-1",
            "phone_number": "+14155550100",
            "status": "active",
            "assigned_agent_id": "agent-1",
        }
    ]

    plan = MIGRATION.build_backfill_plan(legacy, existing)

    assert plan.inserts == []
    assert plan.updates == []


def test_build_backfill_plan_assigns_an_existing_unassigned_number() -> None:
    """An existing safe row is reused and remains enabled for reactivation."""
    plan = MIGRATION.build_backfill_plan(
        [
            {
                "organization_id": "org-1",
                "agent_id": "agent-1",
                "phone_number": "+14155550100",
                "is_active": False,
                "created_at": None,
            }
        ],
        [
            {
                "id": "phone-1",
                "organization_id": "org-1",
                "phone_number": "+14155550100",
                "status": "purchased",
                "assigned_agent_id": None,
            }
        ],
    )

    assert plan.inserts == []
    assert plan.updates == [
        {
            "id": "phone-1",
            "assigned_agent_id": "agent-1",
            "is_incoming_enabled": True,
            "status": "active",
        }
    ]


def test_build_backfill_plan_repairs_existing_assignment_state() -> None:
    """An assigned legacy number is made routable during the backfill."""
    plan = MIGRATION.build_backfill_plan(
        [
            {
                "organization_id": "org-1",
                "agent_id": "agent-1",
                "phone_number": "+14155550100",
                "is_active": True,
                "created_at": None,
            }
        ],
        [
            {
                "id": "phone-1",
                "organization_id": "org-1",
                "phone_number": "+14155550100",
                "status": "purchased",
                "assigned_agent_id": "agent-1",
                "is_incoming_enabled": False,
            }
        ],
    )

    assert plan.updates == [
        {
            "id": "phone-1",
            "assigned_agent_id": "agent-1",
            "is_incoming_enabled": True,
            "status": "active",
        }
    ]


def test_build_backfill_plan_rejects_conflicting_legacy_assignments() -> None:
    """A number shared by multiple agents must be resolved before deployment."""
    with pytest.raises(MIGRATION.BackfillConflict, match="assigned to multiple agents"):
        MIGRATION.build_backfill_plan(
            [
                {
                    "organization_id": "org-1",
                    "agent_id": "agent-1",
                    "phone_number": "+14155550100",
                    "is_active": True,
                    "created_at": None,
                },
                {
                    "organization_id": "org-1",
                    "agent_id": "agent-2",
                    "phone_number": "+1 (415) 555-0100",
                    "is_active": True,
                    "created_at": None,
                },
            ],
            [],
        )


def test_build_backfill_plan_rejects_existing_assignment_conflict() -> None:
    """An already assigned row cannot be silently moved during backfill."""
    with pytest.raises(MIGRATION.BackfillConflict, match="already assigned"):
        MIGRATION.build_backfill_plan(
            [
                {
                    "organization_id": "org-1",
                    "agent_id": "agent-1",
                    "phone_number": "+14155550100",
                    "is_active": True,
                    "created_at": None,
                }
            ],
            [
                {
                    "id": "phone-1",
                    "organization_id": "org-1",
                    "phone_number": "+14155550100",
                    "status": "active",
                    "assigned_agent_id": "agent-2",
                }
            ],
        )


def test_build_backfill_plan_rejects_duplicate_existing_rows() -> None:
    """Duplicate rows for one organization and number must fail closed."""
    with pytest.raises(MIGRATION.BackfillConflict, match="multiple"):
        MIGRATION.build_backfill_plan(
            [
                {
                    "organization_id": "org-1",
                    "agent_id": "agent-1",
                    "phone_number": "415-555-0100",
                    "is_active": True,
                    "created_at": None,
                }
            ],
            [
                {
                    "id": "phone-1",
                    "organization_id": "org-1",
                    "phone_number": "+14155550100",
                    "status": "active",
                    "assigned_agent_id": None,
                },
                {
                    "id": "phone-2",
                    "organization_id": "org-1",
                    "phone_number": "+14155550100",
                    "status": "active",
                    "assigned_agent_id": None,
                },
            ],
        )


def test_build_backfill_plan_creates_customer_managed_record() -> None:
    """A missing legacy row receives non-rental, customer-managed defaults."""
    plan = MIGRATION.build_backfill_plan(
        [
            {
                "organization_id": "org-1",
                "agent_id": "agent-1",
                "phone_number": "+441632960000",
                "is_active": True,
                "created_at": None,
            }
        ],
        [],
    )

    assert plan.updates == []
    assert plan.inserts == [
        {
            "organization_id": "org-1",
            "phone_number": "+441632960000",
            "provider": "twilio",
            "provider_sid": None,
            "phone_number_type": "local",
            "country_code": "ZZ",
            "area_code": None,
            "monthly_cost_credits": 0,
            "status": "active",
            "assigned_agent_id": "agent-1",
            "is_incoming_enabled": True,
            "is_outgoing_enabled": False,
            "billing_status": "active",
            "billing_mode": "none",
            "provisioning_source": "customer",
            "management_mode": "customer_managed",
            "configuration_status": "configured",
        }
    ]
