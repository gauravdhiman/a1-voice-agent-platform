"""Approved credit top-up prices use one consistent value per credit."""

from src.billing.credit_catalog import CREDIT_PACKS


def test_launch_credit_packs_have_consistent_value_and_call_minute_equivalents():
    assert [
        (pack["credit_amount"], int(pack["price_usd"] * 100))
        for pack in CREDIT_PACKS
    ] == [(200, 500), (400, 1000), (1000, 2500)]
    assert [pack["credit_amount"] // 10 for pack in CREDIT_PACKS] == [20, 40, 100]
    assert {
        pack["price_usd"] / pack["credit_amount"] for pack in CREDIT_PACKS
    } == {0.025}
