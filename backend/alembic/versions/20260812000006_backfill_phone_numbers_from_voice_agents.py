"""Backfill the phone-number source of truth from legacy voice agents.

This is a forward-only data migration.  It deliberately does not call Twilio,
charge credits, or clear ``voice_agents.phone_number``.  Keeping the legacy
column during the rollout gives us a safe rollback window while all new
routing reads from ``phone_numbers``.
"""

import re
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260812000006"
down_revision: Union[str, None] = "20260812000005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


class BackfillConflict(ValueError):
    """Raised when legacy data cannot be migrated without changing ownership."""


@dataclass
class BackfillPlan:
    """The deterministic inserts and updates required for a legacy backfill."""

    inserts: list[dict[str, Any]] = field(default_factory=list)
    updates: list[dict[str, Any]] = field(default_factory=list)


def normalize_legacy_phone(value: str) -> str:
    """Normalize a historical phone value to E.164 without guessing geography.

    Ten-digit and eleven-digit North American values are interpreted as US
    numbers.  Values that already begin with ``+`` are accepted as
    international E.164 values.  Other formats fail the migration so an
    operator can resolve them explicitly instead of creating a bad route.

    Args:
        value: Historical value from ``voice_agents.phone_number``.

    Returns:
        Canonical E.164 phone number.

    Raises:
        ValueError: If the value is empty, ambiguous, or outside E.164 limits.
    """
    raw = str(value or "").strip()
    if not raw:
        raise ValueError("Phone number is empty")

    digits = re.sub(r"\D", "", raw)
    if raw.startswith("+"):
        normalized = f"+{digits}"
    elif len(digits) == 10:
        normalized = f"+1{digits}"
    elif len(digits) == 11 and digits.startswith("1"):
        normalized = f"+{digits}"
    else:
        raise ValueError(f"Cannot safely normalize legacy phone number {value!r}")

    if not re.fullmatch(r"\+[1-9]\d{7,14}", normalized):
        raise ValueError(f"Legacy phone number is not valid E.164: {value!r}")
    return normalized


def _country_code(phone_number: str) -> str:
    """Return the known ISO country code, or ``ZZ`` when geography is unknown."""
    return "US" if phone_number.startswith("+1") else "ZZ"


def _area_code(phone_number: str) -> str | None:
    """Extract a North American area code when the number is a US number."""
    if phone_number.startswith("+1") and len(phone_number) >= 5:
        return phone_number[2:5]
    return None


def build_backfill_plan(
    legacy_rows: Sequence[Mapping[str, Any]],
    existing_rows: Sequence[Mapping[str, Any]],
) -> BackfillPlan:
    """Build an idempotent, conflict-aware plan for the data migration.

    Args:
        legacy_rows: Rows from ``voice_agents`` with organization, agent, and
            phone fields.
        existing_rows: Rows already present in ``phone_numbers``.

    Returns:
        A plan containing only missing inserts and safe assignments.

    Raises:
        BackfillConflict: If two agents claim a number, or an existing number
            is assigned to a different agent.
        ValueError: If a non-empty legacy value cannot be normalized safely.

    Notes:
        ``is_incoming_enabled`` describes the number mapping, not agent
        activation. The router separately requires the assigned agent to be
        active, so keeping the mapping enabled lets an inactive migrated agent
        receive calls immediately when it is later activated.
    """
    candidates: dict[tuple[str, str], Mapping[str, Any]] = {}
    for row in legacy_rows:
        raw_phone = row.get("phone_number")
        if raw_phone is None or not str(raw_phone).strip():
            continue

        normalized = normalize_legacy_phone(str(raw_phone))
        key = (str(row["organization_id"]), normalized)
        previous = candidates.get(key)
        if previous and str(previous["agent_id"]) != str(row["agent_id"]):
            raise BackfillConflict(
                f"Number {normalized} is assigned to multiple agents in "
                f"organization {key[0]}"
            )
        candidates[key] = row

    existing_by_key: dict[tuple[str, str], Mapping[str, Any]] = {}
    for row in existing_rows:
        key = (
            str(row["organization_id"]),
            normalize_legacy_phone(str(row["phone_number"])),
        )
        if key in existing_by_key:
            raise BackfillConflict(
                f"Number {key[1]} has multiple phone_numbers rows in "
                f"organization {key[0]}"
            )
        existing_by_key[key] = row

    plan = BackfillPlan()
    for (organization_id, normalized), row in candidates.items():
        existing = existing_by_key.get((organization_id, normalized))
        agent_id = str(row["agent_id"])

        if existing:
            status = str(existing.get("status") or "")
            if status in {"cancelled", "disconnected"}:
                raise BackfillConflict(
                    f"Number {normalized} already has a terminal phone_numbers "
                    f"row ({existing.get('id')}); resolve it before backfill"
                )

            assigned_agent_id = existing.get("assigned_agent_id")
            if assigned_agent_id and str(assigned_agent_id) != agent_id:
                raise BackfillConflict(
                    f"Number {normalized} is already assigned to "
                    f"agent {assigned_agent_id}"
                )
            if assigned_agent_id:
                incoming_enabled = bool(existing.get("is_incoming_enabled", True))
                if status == "purchased" or not incoming_enabled:
                    plan.updates.append(
                        {
                            "id": str(existing["id"]),
                            "assigned_agent_id": agent_id,
                            "is_incoming_enabled": True,
                            "status": "active" if status == "purchased" else status,
                        }
                    )
                continue
            if not assigned_agent_id:
                plan.updates.append(
                    {
                        "id": str(existing["id"]),
                        "assigned_agent_id": agent_id,
                        "is_incoming_enabled": True,
                        "status": "active",
                    }
                )
            continue

        plan.inserts.append(
            {
                "organization_id": organization_id,
                "phone_number": normalized,
                "provider": "twilio",
                "provider_sid": None,
                "phone_number_type": "local",
                "country_code": _country_code(normalized),
                "area_code": _area_code(normalized),
                "monthly_cost_credits": 0,
                "status": "active",
                "assigned_agent_id": agent_id,
                "is_incoming_enabled": True,
                "is_outgoing_enabled": False,
                "billing_status": "active",
                "billing_mode": "none",
                "provisioning_source": "customer",
                "management_mode": "customer_managed",
                "configuration_status": "configured",
            }
        )

    return plan


def upgrade() -> None:
    """Backfill legacy agent numbers before the new router is deployed.

    The Alembic transaction makes the migration atomic.  Any invalid value or
    ownership conflict raises before the application deployment can proceed.
    """
    bind = op.get_bind()
    legacy_rows = (
        bind.execute(
            sa.text(
                """
            SELECT organization_id::text AS organization_id,
                   id::text AS agent_id,
                   phone_number
            FROM voice_agents
            WHERE phone_number IS NOT NULL
              AND btrim(phone_number) <> ''
            ORDER BY organization_id, id
            """
            )
        )
        .mappings()
        .all()
    )
    existing_rows = (
        bind.execute(
            sa.text(
                """
            SELECT id::text AS id,
                   organization_id::text AS organization_id,
                   phone_number,
                   status,
                   assigned_agent_id::text AS assigned_agent_id,
                   is_incoming_enabled
            FROM phone_numbers
            """
            )
        )
        .mappings()
        .all()
    )

    try:
        plan = build_backfill_plan(legacy_rows, existing_rows)
    except (BackfillConflict, ValueError) as exc:
        raise RuntimeError(
            "Phone-number data migration blocked; resolve legacy data before "
            f"deploying the phone_numbers source-of-truth change: {exc}"
        ) from exc

    for update in plan.updates:
        bind.execute(
            sa.text(
                """
                UPDATE phone_numbers
                SET assigned_agent_id = CAST(:assigned_agent_id AS uuid),
                    is_incoming_enabled = :is_incoming_enabled,
                    status = :status,
                    updated_at = now()
                WHERE id = CAST(:id AS uuid)
                """
            ),
            update,
        )

    for insert in plan.inserts:
        bind.execute(
            sa.text(
                """
                INSERT INTO phone_numbers (
                    organization_id, phone_number, provider, provider_sid,
                    phone_number_type, country_code, area_code,
                    monthly_cost_credits, status, assigned_agent_id,
                    is_incoming_enabled, is_outgoing_enabled, billing_status,
                    billing_mode, provisioning_source, management_mode,
                    configuration_status
                ) VALUES (
                    CAST(:organization_id AS uuid), :phone_number, :provider,
                    :provider_sid, :phone_number_type, :country_code,
                    :area_code, :monthly_cost_credits, :status,
                    CAST(:assigned_agent_id AS uuid), :is_incoming_enabled,
                    :is_outgoing_enabled, :billing_status, :billing_mode,
                    :provisioning_source, :management_mode,
                    :configuration_status
                )
                """
            ),
            insert,
        )

    expected = len(legacy_rows)
    migrated = bind.execute(
        sa.text(
            """
            SELECT count(*)
            FROM voice_agents va
            JOIN phone_numbers pn
              ON pn.organization_id = va.organization_id
             AND pn.assigned_agent_id = va.id
            WHERE va.phone_number IS NOT NULL
              AND btrim(va.phone_number) <> ''
            """
        )
    ).scalar_one()
    if migrated != expected:
        raise RuntimeError(
            "Phone-number data migration verification failed: "
            f"expected {expected} assignments, found {migrated}"
        )


def downgrade() -> None:
    """Intentionally keep backfilled rows; data migrations are forward-only."""
