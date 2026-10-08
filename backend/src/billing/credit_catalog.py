"""Approved one-time credit top-up catalog for Stripe setup and billing UI."""

from typing import TypedDict


class CreditPackDefinition(TypedDict):
    """Stripe product fields for one customer-facing credit pack."""

    name: str
    description: str
    credit_amount: int
    price_usd: float


# At the default voice rate of 10 credits per connected minute, packs lower the
# effective call-minute rate in small steps while keeping the entry pack at $5.
CREDIT_PACKS: tuple[CreditPackDefinition, ...] = (
    {
        "name": "200 Credits Pack",
        "description": "200 credits for occasional extra usage",
        "credit_amount": 200,
        "price_usd": 5.00,
    },
    {
        "name": "500 Credits Pack",
        "description": (
            "500 credits for regular extra usage at a lower call-minute rate"
        ),
        "credit_amount": 500,
        "price_usd": 12.00,
    },
    {
        "name": "1000 Credits Pack",
        "description": (
            "1000 credits for higher extra usage at a lower call-minute rate"
        ),
        "credit_amount": 1000,
        "price_usd": 23.00,
    },
    {
        "name": "2000 Credits Pack",
        "description": (
            "2000 credits for sustained usage at the lowest call-minute rate"
        ),
        "credit_amount": 2000,
        "price_usd": 44.00,
    },
)
