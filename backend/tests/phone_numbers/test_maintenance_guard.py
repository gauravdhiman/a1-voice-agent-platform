"""External maintenance coordinates phone mutations by organization."""

import asyncio
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException
from src.phone_numbers.maintenance_guard import phone_mutation_guard
from src.phone_numbers.service import PhoneNumberRentalRunResult, PhoneNumberService


@pytest.mark.asyncio
async def test_external_guard_uses_organization_key_and_releases():
    organization = uuid4()
    coordinator = MagicMock()
    coordinator.acquire = AsyncMock(return_value="owner")
    coordinator.release_guard = AsyncMock()
    with (
        patch(
            "src.phone_numbers.maintenance_guard.settings",
            SimpleNamespace(maintenance_mode="external"),
        ),
        patch(
            "src.phone_numbers.maintenance_guard.supabase_config",
            SimpleNamespace(service_client=object()),
        ),
        patch(
            "src.phone_numbers.maintenance_guard.PostgresRunCoordinator",
            return_value=coordinator,
        ),
    ):
        async with phone_mutation_guard(organization):
            pass
    coordinator.acquire.assert_awaited_once_with(f"phone-org:{organization}")
    coordinator.release_guard.assert_awaited_once_with(
        f"phone-org:{organization}", "owner"
    )


@pytest.mark.asyncio
async def test_busy_guard_rejects_conflicting_mutation():
    coordinator = MagicMock()
    coordinator.acquire = AsyncMock(return_value=None)
    with (
        patch(
            "src.phone_numbers.maintenance_guard.settings",
            SimpleNamespace(maintenance_mode="external"),
        ),
        patch(
            "src.phone_numbers.maintenance_guard.supabase_config",
            SimpleNamespace(service_client=object()),
        ),
        patch(
            "src.phone_numbers.maintenance_guard.PostgresRunCoordinator",
            return_value=coordinator,
        ),
    ):
        with pytest.raises(HTTPException) as error:
            async with phone_mutation_guard(uuid4()):
                pytest.fail("conflicting mutation must not execute")
    assert error.value.status_code == 409


@pytest.mark.asyncio
async def test_cancelled_guard_retains_claim():
    coordinator = MagicMock()
    coordinator.acquire = AsyncMock(return_value="owner")
    coordinator.release_guard = AsyncMock()
    with (
        patch(
            "src.phone_numbers.maintenance_guard.settings",
            SimpleNamespace(maintenance_mode="external"),
        ),
        patch(
            "src.phone_numbers.maintenance_guard.supabase_config",
            SimpleNamespace(service_client=object()),
        ),
        patch(
            "src.phone_numbers.maintenance_guard.PostgresRunCoordinator",
            return_value=coordinator,
        ),
    ):
        with pytest.raises(asyncio.CancelledError):
            async with phone_mutation_guard(uuid4()):
                raise asyncio.CancelledError()
    coordinator.release_guard.assert_not_awaited()


@pytest.mark.asyncio
async def test_worker_reloads_rows_after_acquiring_organization_guard():
    organization = uuid4()
    client = MagicMock()
    table = client.table.return_value
    table.select.return_value = table
    table.in_.return_value = table
    table.eq.return_value = table
    table.order.return_value = table
    table.limit.return_value = table
    table.execute.side_effect = [
        SimpleNamespace(data=[{"organization_id": str(organization)}]),
        SimpleNamespace(data=[]),
    ]
    guarded = []

    @asynccontextmanager
    async def guard(org, *, force=False):
        guarded.append((org, force))
        yield

    with patch(
        "src.phone_numbers.service.supabase_config", SimpleNamespace(client=client)
    ):
        service = PhoneNumberService()
    service.supabase = client
    service._process_rental_rows = AsyncMock(return_value=PhoneNumberRentalRunResult())
    with (
        patch("src.phone_numbers.service.phone_mutation_guard", guard),
        patch(
            "src.phone_numbers.service.platform_phone_number_settings_service."
            "get_settings",
            new=AsyncMock(return_value=object()),
        ),
    ):
        result = await service.process_due_rentals(guarded=True)
    assert result.errors == 0
    assert guarded == [(organization, True)]
    assert service._process_rental_rows.await_args.args[0] == []


@pytest.mark.asyncio
async def test_worker_defers_busy_organization_for_next_tick():
    organization = uuid4()
    client = MagicMock()
    table = client.table.return_value
    table.select.return_value = table
    table.in_.return_value = table
    table.order.return_value = table
    table.limit.return_value = table
    table.execute.return_value = SimpleNamespace(
        data=[{"organization_id": str(organization)}]
    )

    @asynccontextmanager
    async def busy_guard(org, *, force=False):
        raise HTTPException(status_code=409)
        yield

    with patch(
        "src.phone_numbers.service.supabase_config", SimpleNamespace(client=client)
    ):
        service = PhoneNumberService()
    service.supabase = client
    service._process_rental_rows = AsyncMock()
    with (
        patch("src.phone_numbers.service.phone_mutation_guard", busy_guard),
        patch(
            "src.phone_numbers.service.platform_phone_number_settings_service."
            "get_settings",
            new=AsyncMock(return_value=object()),
        ),
    ):
        result = await service.process_due_rentals(guarded=True)
    assert result.deferred == 1
    assert result.errors == 0
    service._process_rental_rows.assert_not_awaited()


@pytest.mark.asyncio
async def test_guarded_rental_scan_reads_all_keyset_pages():
    client = MagicMock()
    table = client.table.return_value
    for method in ("select", "in_", "order", "limit", "gt"):
        getattr(table, method).return_value = table
    first_page = [{"id": str(uuid4())} for _ in range(200)]
    table.execute.side_effect = [
        SimpleNamespace(data=first_page),
        SimpleNamespace(data=[{"id": str(uuid4())}]),
    ]
    with patch(
        "src.phone_numbers.service.supabase_config", SimpleNamespace(client=client)
    ):
        service = PhoneNumberService()
    service.supabase = client
    result = await service._load_guarded_rental_rows()
    assert len(result) == 201
    table.gt.assert_called_once_with("id", first_page[-1]["id"])


@pytest.mark.asyncio
async def test_worker_preserves_guard_when_provider_outcome_is_uncertain():
    organization = uuid4()
    client = MagicMock()
    table = client.table.return_value
    for method in ("select", "in_", "eq", "order", "limit"):
        getattr(table, method).return_value = table
    table.execute.side_effect = [
        SimpleNamespace(data=[{"organization_id": str(organization)}]),
        SimpleNamespace(data=[]),
    ]
    exceptions = []

    @asynccontextmanager
    async def guard(org, *, force=False):
        try:
            yield
        except Exception as exc:
            exceptions.append(exc)
            raise

    with patch(
        "src.phone_numbers.service.supabase_config", SimpleNamespace(client=client)
    ):
        service = PhoneNumberService()
    service.supabase = client
    service._process_rental_rows = AsyncMock(
        return_value=PhoneNumberRentalRunResult(errors=1)
    )
    with (
        patch("src.phone_numbers.service.phone_mutation_guard", guard),
        patch(
            "src.phone_numbers.service.platform_phone_number_settings_service."
            "get_settings",
            new=AsyncMock(return_value=object()),
        ),
    ):
        result = await service.process_due_rentals(guarded=True)
    assert result.errors > 0
    assert len(exceptions) == 1
