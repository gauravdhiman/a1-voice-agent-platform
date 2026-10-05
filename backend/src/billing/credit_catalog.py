"""Approved one-time credit top-up catalog for Stripe setup and billing UI."""

from typing import TypedDict


class CreditPackDefinition(TypedDict):
    """Stripe product fields for one customer-facing credit pack."""

    name: str
    description: str
    credit_amount: int
    price_usd: float


# 40 credits are $1 across all launch packs. No pack advertises an artificial
# bulk discount; the checkout price and issued credits remain the source of truth.
CREDIT_PACKS: tuple[CreditPackDefinition, ...] = (
    {
        "name": "200 Credits Pack",
        "description": "200 credits for occasional extra usage",
        "credit_amount": 200,
        "price_usd": 5.00,
    },
    {
        "name": "400 Credits Pack",
        "description": "400 credits for regular extra usage",
        "credit_amount": 400,
        "price_usd": 10.00,
    },
    {
        "name": "1000 Credits Pack",
        "description": "1000 credits for higher extra usage",
        "credit_amount": 1000,
        "price_usd": 25.00,
    },
)
