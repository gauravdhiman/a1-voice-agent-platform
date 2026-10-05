from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

from src.billing.stripe_service import StripeService
from src.billing.webhook_handler import (
    handle_checkout_session_completed,
    handle_payment_intent_succeeded,
    handle_stripe_webhook,
)


@pytest.mark.asyncio
async def test_credit_checkout_copies_catalog_amount_to_session_and_payment_intent():
    session = Mock(id="cs_credits", url="https://checkout.stripe.test/session")
    with patch(
        "src.billing.stripe_service.stripe.checkout.Session.create",
        return_value=session,
    ) as create_session:
        await StripeService().create_credits_checkout_session(
            price_id="price_credits",
            customer_id="cus_org",
            organization_id="123e4567-e89b-42d3-a456-426614174000",
            product_id="credit-pack-200",
            credit_amount=200,
        )

    create_session.assert_called_once()
    options = create_session.call_args.kwargs
    expected_metadata = {
        "organization_id": "123e4567-e89b-42d3-a456-426614174000",
        "product_id": "credit-pack-200",
        "credit_amount": "200",
        "type": "credits",
    }
    assert options["metadata"] == expected_metadata
    assert options["payment_intent_data"]["metadata"] == expected_metadata


@pytest.mark.asyncio
async def test_unpaid_credit_checkout_completion_does_not_grant_credits():
    organization_id = uuid4()
    event = {
        "data": {
            "object": {
                "id": "cs_delayed_payment",
                "mode": "payment",
                "payment_status": "unpaid",
                "payment_intent": "pi_delayed_payment",
                "metadata": {
                    "organization_id": str(organization_id),
                    "product_id": "credit-pack-200",
                    "credit_amount": "200",
                    "type": "credits",
                },
            }
        }
    }

    with patch(
        "src.billing.webhook_handler.billing_service.add_purchased_credits",
        new_callable=AsyncMock,
    ) as grant_credits:
        await handle_checkout_session_completed(event)

    grant_credits.assert_not_awaited()


@pytest.mark.asyncio
async def test_paid_credit_checkout_completion_grants_using_payment_intent_id():
    organization_id = uuid4()
    event = {
        "data": {
            "object": {
                "id": "cs_paid",
                "mode": "payment",
                "payment_status": "paid",
                "payment_intent": {"id": "pi_paid"},
                "metadata": {
                    "organization_id": str(organization_id),
                    "product_id": "credit-pack-200",
                    "credit_amount": "200",
                    "type": "credits",
                },
            }
        }
    }

    with patch(
        "src.billing.webhook_handler.billing_service.add_purchased_credits",
        new_callable=AsyncMock,
    ) as grant_credits:
        await handle_checkout_session_completed(event)

    grant_credits.assert_awaited_once_with(
        organization_id=organization_id,
        credits=200,
        stripe_payment_intent_id="pi_paid",
        description="Credit purchase - 200 credits",
    )


@pytest.mark.asyncio
async def test_successful_credit_payment_intent_grants_once_with_stable_payment_id():
    organization_id = uuid4()
    event = {
        "data": {
            "object": {
                "id": "pi_async_paid",
                "customer": "cus_org",
                "amount": 500,
                "currency": "usd",
                "created": 1_790_000_000,
                "metadata": {
                    "organization_id": str(organization_id),
                    "product_id": "credit-pack-200",
                    "credit_amount": "200",
                    "type": "credits",
                },
            }
        }
    }

    with (
        patch(
            "src.billing.webhook_handler.billing_service.create_billing_history",
            new_callable=AsyncMock,
        ),
        patch(
            "src.billing.webhook_handler.billing_service.add_purchased_credits",
            new_callable=AsyncMock,
        ) as grant_credits,
    ):
        await handle_payment_intent_succeeded(event)

    grant_credits.assert_awaited_once_with(
        organization_id=organization_id,
        credits=200,
        stripe_payment_intent_id="pi_async_paid",
        description="Credit purchase - 200 credits",
    )


@pytest.mark.asyncio
async def test_async_checkout_success_event_uses_paid_checkout_fulfillment():
    event = {
        "type": "checkout.session.async_payment_succeeded",
        "data": {"object": {"id": "cs_async_paid"}},
    }

    with (
        patch(
            "src.billing.webhook_handler.settings",
            SimpleNamespace(stripe_webhook_secret="whsec_test"),
        ),
        patch(
            "src.billing.webhook_handler.stripe_service.construct_webhook_event",
            return_value=event,
        ),
        patch(
            "src.billing.webhook_handler.handle_checkout_session_completed",
            new_callable=AsyncMock,
        ) as process_paid_session,
    ):
        await handle_stripe_webhook(b"signed-payload", "test-signature")

    process_paid_session.assert_awaited_once_with(event)
