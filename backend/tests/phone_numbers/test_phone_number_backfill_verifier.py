"""Tests for the production verification command for the phone backfill."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

VERIFIER_PATH = (
    Path(__file__).parents[2]
    / ".."
    / "scripts"
    / "deploy"
    / "verify_phone_number_backfill.py"
).resolve()
SPEC = spec_from_file_location("phone_number_backfill_verifier", VERIFIER_PATH)
assert SPEC and SPEC.loader
VERIFIER = module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFIER)


def test_find_unmigrated_legacy_rows_accepts_assigned_normalized_rows() -> None:
    """A canonical assigned phone_numbers row satisfies the postcondition."""
    assert (
        VERIFIER.find_unmigrated_legacy_rows(
            [
                {
                    "organization_id": "org-1",
                    "agent_id": "agent-1",
                    "phone_number": "(415) 555-0100",
                }
            ],
            [
                {
                    "organization_id": "org-1",
                    "phone_number": "+14155550100",
                    "assigned_agent_id": "agent-1",
                }
            ],
        )
        == []
    )


def test_find_unmigrated_legacy_rows_accepts_a_later_unassigned_row() -> None:
    """A later user unassignment must not block a future deployment."""
    assert (
        VERIFIER.find_unmigrated_legacy_rows(
            [
                {
                    "organization_id": "org-1",
                    "agent_id": "agent-1",
                    "phone_number": "+14155550100",
                }
            ],
            [
                {
                    "organization_id": "org-1",
                    "phone_number": "+14155550100",
                    "assigned_agent_id": None,
                }
            ],
        )
        == []
    )


def test_find_unmigrated_legacy_rows_reports_missing_row() -> None:
    """A legacy phone without any table row blocks deployment."""
    problems = VERIFIER.find_unmigrated_legacy_rows(
        [
            {
                "organization_id": "org-1",
                "agent_id": "agent-1",
                "phone_number": "+14155550100",
            }
        ],
        [],
    )

    assert problems == ["org-1/agent-1: +14155550100"]


def test_find_unmigrated_legacy_rows_reports_invalid_value() -> None:
    """The verifier surfaces invalid legacy data instead of hiding it."""
    with pytest.raises(ValueError, match="Cannot safely normalize"):
        VERIFIER.find_unmigrated_legacy_rows(
            [
                {
                    "organization_id": "org-1",
                    "agent_id": "agent-1",
                    "phone_number": "not-a-number",
                }
            ],
            [],
        )
