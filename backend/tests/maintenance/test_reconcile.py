"""Reconciliation requires explicit verification and a matching claim."""

from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from src.maintenance.reconcile import main


def test_reconciliation_refuses_unverified_provider_outcome():
    client = MagicMock()
    with pytest.raises(SystemExit):
        main(
            ["--job", "phone-rental", "--claim", "owner", "--worker-stopped"],
            client=client,
        )
    client.rpc.assert_not_called()


def test_reconciliation_requires_the_exact_held_claim():
    client = MagicMock()
    client.rpc.return_value.execute.return_value = SimpleNamespace(data=False)
    with pytest.raises(RuntimeError):
        main(
            [
                "--job",
                "phone-rental",
                "--claim",
                "old",
                "--worker-stopped",
                "--provider-outcome-verified",
            ],
            client=client,
        )


def test_verified_reconciliation_uses_service_role_rpc():
    client = MagicMock()
    client.rpc.return_value.execute.return_value = SimpleNamespace(data=True)
    assert (
        main(
            [
                "--job",
                "phone-rental",
                "--claim",
                "owner",
                "--worker-stopped",
                "--provider-outcome-verified",
            ],
            client=client,
        )
        == 0
    )
    client.rpc.assert_called_once_with(
        "reconcile_maintenance_run", {"p_job": "phone-rental", "p_claim": "owner"}
    )


def test_organization_phone_guard_can_be_reconciled():
    client = MagicMock()
    client.rpc.return_value.execute.return_value = SimpleNamespace(data=True)
    job = f"phone-org:{uuid4()}"
    assert (
        main(
            [
                "--job",
                job,
                "--claim",
                "owner",
                "--worker-stopped",
                "--provider-outcome-verified",
            ],
            client=client,
        )
        == 0
    )
    client.rpc.assert_called_once_with(
        "reconcile_maintenance_run", {"p_job": job, "p_claim": "owner"}
    )
