"""Stripe webhook responses acknowledge events only after state processing."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from src.billing.routes import stripe_webhook
from src.billing.webhook_handler import InvalidStripeWebhook


def _request() -> Request:
    messages = [
        {"type": "http.request", "body": b"signed-stripe-payload", "more_body": False}
    ]

    async def receive():
        return messages.pop(0)

    return Request(
        {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "POST",
            "scheme": "https",
            "path": "/api/v1/billing/webhook/stripe",
            "raw_path": b"/api/v1/billing/webhook/stripe",
            "query_string": b"",
            "headers": [(b"stripe-signature", b"test-signature")],
            "client": ("127.0.0.1", 1234),
            "server": ("test", 443),
        },
        receive,
    )


@pytest.mark.asyncio
async def test_webhook_waits_for_processing_before_returning_success():
    with patch(
        "src.billing.routes.handle_stripe_webhook", new_callable=AsyncMock
    ) as process:
        response = await stripe_webhook(_request())

    process.assert_awaited_once_with(b"signed-stripe-payload", "test-signature")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_webhook_returns_retryable_failure_when_processing_fails():
    with patch(
        "src.billing.routes.handle_stripe_webhook",
        new_callable=AsyncMock,
        side_effect=RuntimeError("database unavailable"),
    ):
        with pytest.raises(HTTPException) as error:
            await stripe_webhook(_request())

    assert error.value.status_code == 500
    assert error.value.detail == "Webhook processing failed"


@pytest.mark.asyncio
async def test_webhook_rejects_invalid_signature_as_client_error():
    with patch(
        "src.billing.routes.handle_stripe_webhook",
        new_callable=AsyncMock,
        side_effect=InvalidStripeWebhook("invalid signature"),
    ):
        with pytest.raises(HTTPException) as error:
            await stripe_webhook(_request())

    assert error.value.status_code == 400
    assert error.value.detail == "Invalid Stripe webhook"
