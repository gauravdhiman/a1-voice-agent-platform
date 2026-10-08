"""Approved credit top-ups provide progressively lower call-minute rates."""

from src.billing.credit_catalog import CREDIT_PACKS


def test_launch_credit_packs_have_four_tiers_and_step_down_per_minute_rates():
    assert [
        (pack["credit_amount"], int(pack["price_usd"] * 100)) for pack in CREDIT_PACKS
    ] == [(200, 500), (500, 1200), (1000, 2300), (2000, 4400)]
    assert [pack["credit_amount"] // 10 for pack in CREDIT_PACKS] == [
        20,
        50,
        100,
        200,
    ]

    cents_per_call_minute = [
        int(pack["price_usd"] * 100 * 10 / pack["credit_amount"])
        for pack in CREDIT_PACKS
    ]
    assert cents_per_call_minute == [25, 24, 23, 22]
    assert all(
        earlier > later
        for earlier, later in zip(cents_per_call_minute, cents_per_call_minute[1:])
    )
