"""Tests for the dry-run-first master-data command-line workflow."""

import json
from unittest.mock import AsyncMock, patch

import pytest
from src.master_data import cli
from src.master_data.definitions import build_master_data_catalog


def _preview(*, definition_hash: str = "hash-v1") -> list[dict[str, object]]:
    """Build a minimal preview payload for CLI tests."""
    return [
        {
            "key": "system_pricing",
            "display_name": "System usage pricing",
            "category": "billing",
            "description": "Usage pricing",
            "source": "system_pricing.py",
            "definition_version": "2026.08.13.1",
            "definition_hash": definition_hash,
            "expected_count": 4,
            "current_count": 0,
            "seedable": True,
            "requires_review": False,
            "migration_managed": False,
            "status": "pending",
            "items": [{"key": "voice.minute", "label": "Voice minute"}],
            "payload": [{"event_name": "voice.minute", "credit_cost": 1}],
            "last_run": None,
        }
    ]


def _skill_preview() -> list[dict[str, object]]:
    """Build a preview containing the full source content of one skill."""
    return [
        {
            "key": "platform_skills",
            "display_name": "Platform skill templates",
            "category": "product",
            "description": "Reusable platform skills",
            "source": "skill_seeds.py",
            "definition_version": "2026.08.13.1",
            "definition_hash": "skill-hash",
            "expected_count": 1,
            "current_count": 0,
            "seedable": True,
            "requires_review": False,
            "migration_managed": False,
            "status": "pending",
            "items": [
                {
                    "key": "reservation-booking",
                    "label": "Reservation booking",
                    "description": "Books a reservation",
                }
            ],
            "payload": [
                {
                    "slug": "reservation-booking",
                    "name": "Reservation booking",
                    "description": "Books a reservation",
                    "content": "Ask for the date, time, and party size.",
                    "files": [
                        {
                            "file_path": "references/policy.md",
                            "content": "Reservations require confirmation.",
                        }
                    ],
                }
            ],
            "last_run": None,
        }
    ]


def test_credit_pack_inventory_uses_code_catalog_but_is_not_generic_seedable():
    credit_products = next(
        item
        for item in build_master_data_catalog(tool_names=[])
        if item.key == "credit_products"
    )

    assert credit_products.source.startswith("backend/src/billing/credit_catalog.py")
    assert credit_products.expected_count == 3
    assert credit_products.seedable is False
    assert credit_products.requires_review is True
    assert [pack["credit_amount"] for pack in credit_products.payload] == [
        200,
        400,
        1000,
    ]


class FakeMasterDataService:
    """Async service double used to verify CLI side-effect boundaries."""

    def __init__(self, previews: list[dict[str, object]]) -> None:
        self.previews = previews
        self.seed_domains = AsyncMock(return_value=[])

    async def preview(self) -> list[dict[str, object]]:
        """Return the configured source preview without changing state."""
        return self.previews


def test_default_command_is_read_only_preview(capsys):
    """Running without an apply command prints a plan and never seeds."""
    service = FakeMasterDataService(_preview())

    with patch.object(cli, "MasterDataService", return_value=service):
        exit_code = cli.main([])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "# Master-data review" in output
    assert "system_pricing" in output
    service.seed_domains.assert_not_awaited()


def test_markdown_report_contains_full_skill_content():
    """The Markdown report exposes skill instructions and reference files."""
    plan = cli._plan_payload(_skill_preview())

    report = cli._render_markdown(plan)

    assert "## Storage model" in report
    assert "Ask for the date, time, and party size." in report
    assert "Reservations require confirmation." in report
    assert "reviewable artifact, not a source of truth" in report


def test_apply_rejects_a_plan_when_source_hash_changed(tmp_path, capsys):
    """Apply must stop if the reviewed source differs from the current source."""
    plan_path = tmp_path / "master-data-plan.json"
    plan_path.write_text(
        json.dumps(
            {
                "plan_version": 1,
                "definition_version": "2026.08.13.1",
                "domains": ["system_pricing"],
                "definition_hashes": {"system_pricing": "hash-v1"},
                "catalog": _preview(),
            }
        )
    )
    service = FakeMasterDataService(_preview(definition_hash="hash-v2"))

    with patch.object(cli, "MasterDataService", return_value=service):
        exit_code = cli.main(["apply", "--plan", str(plan_path)])

    assert exit_code == 2
    assert "changed" in capsys.readouterr().err
    service.seed_domains.assert_not_awaited()


def test_reset_is_rejected_in_production(monkeypatch, capsys):
    """Production cannot use reset; corrections must be forward-only."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    service = FakeMasterDataService(_preview())

    with patch.object(cli, "MasterDataService", return_value=service):
        exit_code = cli.main(["apply", "--reset"])

    assert exit_code == 2
    assert "not supported in production" in capsys.readouterr().err
    service.seed_domains.assert_not_awaited()


def test_reset_requires_an_explicit_nonproduction_environment(monkeypatch, capsys):
    """An unset environment must fail closed instead of allowing reset."""
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    service = FakeMasterDataService(_preview())

    with patch.object(cli, "MasterDataService", return_value=service):
        exit_code = cli.main(["apply", "--reset"])

    assert exit_code == 2
    assert "explicit non-production" in capsys.readouterr().err
    service.seed_domains.assert_not_awaited()


def test_apply_passes_reviewed_hashes_to_service(tmp_path):
    """A reviewed plan hash is forwarded to the service before writes begin."""
    plan_path = tmp_path / "master-data-plan.json"
    plan_path.write_text(
        json.dumps(
            {
                "plan_version": 1,
                "definition_version": "2026.08.13.1",
                "domains": ["system_pricing"],
                "definition_hashes": {"system_pricing": "hash-v1"},
                "catalog": _preview(),
            }
        )
    )
    service = FakeMasterDataService(_preview())

    with patch.object(cli, "MasterDataService", return_value=service):
        exit_code = cli.main(["apply", "--plan", str(plan_path)])

    assert exit_code == 0
    service.seed_domains.assert_awaited_once_with(
        ["system_pricing"],
        triggered_by=None,
        reset=False,
        expected_definition_hashes={"system_pricing": "hash-v1"},
    )


def test_apply_rejects_a_plan_with_no_seedable_domains(tmp_path, capsys):
    """A review-only plan must never fall through to the service's all-domains default."""
    plan_path = tmp_path / "review-only-plan.json"
    plan_path.write_text(
        json.dumps(
            {
                "plan_version": 1,
                "definition_version": "2026.08.13.1",
                "domains": [],
                "definition_hashes": {"plan_catalog": "hash-v1"},
            }
        )
    )
    service = FakeMasterDataService(_preview())

    with patch.object(cli, "MasterDataService", return_value=service):
        exit_code = cli.main(["apply", "--plan", str(plan_path)])

    assert exit_code == 2
    assert "no seedable domains" in capsys.readouterr().err
    service.seed_domains.assert_not_awaited()


def test_apply_rejects_a_different_definition_version(tmp_path, capsys):
    """Apply must reject a plan created by an incompatible source catalog."""
    plan_path = tmp_path / "old-master-data-plan.json"
    plan_path.write_text(
        json.dumps(
            {
                "plan_version": 1,
                "definition_version": "2025.01.01.1",
                "domains": ["system_pricing"],
                "definition_hashes": {"system_pricing": "hash-v1"},
                "catalog": _preview(),
            }
        )
    )
    service = FakeMasterDataService(_preview())

    with patch.object(cli, "MasterDataService", return_value=service):
        exit_code = cli.main(["apply", "--plan", str(plan_path)])

    assert exit_code == 2
    assert "definition version" in capsys.readouterr().err
    service.seed_domains.assert_not_awaited()


@pytest.mark.parametrize(
    ("plan", "error_message"),
    [
        ([], "JSON object"),
        (
            {
                "plan_version": 1,
                "definition_version": "2026.08.13.1",
                "domains": ["system_pricing", 42],
                "definition_hashes": {"system_pricing": "hash-v1"},
                "catalog": _preview(),
            },
            "domains",
        ),
        (
            {
                "plan_version": 1,
                "definition_version": "2026.08.13.1",
                "domains": ["system_pricing", "system_pricing"],
                "definition_hashes": {"system_pricing": "hash-v1"},
            },
            "duplicate",
        ),
        (
            {
                "plan_version": 1,
                "definition_version": "2026.08.13.1",
                "domains": ["system_pricing"],
                "definition_hashes": [],
            },
            "definition_hashes",
        ),
        (
            {
                "plan_version": 1,
                "definition_version": "2026.08.13.1",
                "domains": ["system_pricing"],
                "definition_hashes": {},
            },
            "missing definition hashes",
        ),
        (
            {
                "plan_version": 1,
                "definition_version": "2026.08.13.1",
                "domains": ["system_pricing"],
                "definition_hashes": {"system_pricing": "hash-v1"},
                "catalog": [],
            },
            "catalog entry",
        ),
    ],
)
def test_apply_rejects_malformed_review_plans(tmp_path, capsys, plan, error_message):
    """Malformed or ambiguous review artifacts must never reach the service."""
    plan_path = tmp_path / "malformed-master-data-plan.json"
    plan_path.write_text(json.dumps(plan))
    service = FakeMasterDataService(_preview())

    with patch.object(cli, "MasterDataService", return_value=service):
        exit_code = cli.main(["apply", "--plan", str(plan_path)])

    assert exit_code == 2
    assert error_message in capsys.readouterr().err
    service.seed_domains.assert_not_awaited()


def test_apply_rejects_a_modified_review_catalog(tmp_path, capsys):
    """Apply must not trust a plan whose reviewed payload was edited."""
    plan = {
        "plan_version": 1,
        "definition_version": "2026.08.13.1",
        "domains": ["system_pricing"],
        "definition_hashes": {"system_pricing": "hash-v1"},
        "catalog": _preview(),
    }
    plan["catalog"][0]["payload"][0]["credit_cost"] = 999
    plan_path = tmp_path / "edited-master-data-plan.json"
    plan_path.write_text(json.dumps(plan))
    service = FakeMasterDataService(_preview())

    with patch.object(cli, "MasterDataService", return_value=service):
        exit_code = cli.main(["apply", "--plan", str(plan_path)])

    assert exit_code == 2
    assert "reviewed catalog" in capsys.readouterr().err
    service.seed_domains.assert_not_awaited()
