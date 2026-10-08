"""Billing UI contracts with deterministic auth and provider boundary fixtures."""

import json
import re

import pytest
from helpers import (
    setup_billing_context,
    setup_billing_plans_context,
    setup_credit_products_context,
    signin_user,
)
from playwright.sync_api import Page, expect

TEST_ORGANIZATION_ID = "test-org-id"


@pytest.fixture
def billing_page(page: Page, base_url: str, step):
    """Open an entitled organization's billing page using supported API shapes."""
    organization = {
        "id": TEST_ORGANIZATION_ID,
        "name": "Test Organization",
        "slug": "test-org",
        "is_active": True,
        "created_at": "2026-10-07T00:00:00Z",
        "updated_at": "2026-10-07T00:00:00Z",
    }
    page.route(
        re.compile(r".*/api/v1/organizations(?:\?.*)?$"),
        lambda route: route.fulfill(
            status=200, content_type="application/json", body=json.dumps([organization])
        ),
    )
    page.route(
        re.compile(f".*/api/v1/organizations/{TEST_ORGANIZATION_ID}(?:\\?.*)?$"),
        lambda route: route.fulfill(
            status=200, content_type="application/json", body=json.dumps(organization)
        ),
    )
    page.route(
        re.compile(f".*/api/v1/billing/summary/{TEST_ORGANIZATION_ID}.*"),
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    "organization_id": TEST_ORGANIZATION_ID,
                    "subscription": None,
                    "credit_balance": 1250,
                    "current_period_usage": 150,
                    "next_billing_date": None,
                    "amount_due": None,
                }
            ),
        ),
    )
    page.route(
        re.compile(f".*/api/v1/billing/credits/{TEST_ORGANIZATION_ID}.*"),
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    "organization_id": TEST_ORGANIZATION_ID,
                    "balance": {
                        "total_credits": 1250,
                        "subscription_credits": 1000,
                        "purchased_credits": 250,
                    },
                    "total_credits": 1250,
                    "subscription_credits": 1000,
                    "purchased_credits": 250,
                    "expiring_soon": 100,
                    "expires_at": None,
                    "period_start": None,
                    "period_end": None,
                    "period_credits_granted": 1250,
                    "period_credits_used": 150,
                    "period_credits_remaining": 1100,
                    "usage_by_category": [],
                    "transactions": [],
                }
            ),
        ),
    )
    setup_billing_context(page)
    setup_billing_plans_context(page)
    setup_credit_products_context(page, organization_id=TEST_ORGANIZATION_ID)
    page.route(
        re.compile(r".*/api/v1/billing/.*history.*"),
        lambda route: route.fulfill(
            status=200, content_type="application/json", body="[]"
        ),
    )
    step("Sign in and open the billing page")
    signin_user(page, base_url)
    page.goto(f"{base_url}/organization/billing?org_id={TEST_ORGANIZATION_ID}")
    expect(page.get_by_role("tab", name="Credits")).to_be_visible()
    return page


def test_billing_page_functionality(billing_page: Page, step):
    """All tabs must render their published fixture data."""
    page = billing_page
    step("Verify the billing overview's balance")
    expect(page.get_by_text("1,250", exact=True).first).to_be_visible()
    step("Verify the published plan catalog")
    page.get_by_role("tab", name="Plans").click()
    expect(page.get_by_text("Pro", exact=True).first).to_be_visible()
    expect(
        page.get_by_text(re.compile(r"^\$79\.00\s*/\s*month$")).first
    ).to_be_visible()

    step("Verify every credit pack and its rate")
    page.get_by_role("tab", name="Credits").click()
    section = page.get_by_test_id("credit-purchase-section")
    expected_packs = (
        (200, "$5.00", 20),
        (500, "$12.00", 50),
        (1000, "$23.00", 100),
        (2000, "$44.00", 200),
    )
    for amount, price, minutes in expected_packs:
        expect(
            section.get_by_text(f"{amount} Credits Pack", exact=True)
        ).to_be_visible()
        expect(section.get_by_text(price, exact=True)).to_be_visible()
        expect(
            section.get_by_text(f"Up to {minutes} call minutes", exact=True)
        ).to_be_visible()
    for rate in ("$0.25", "$0.24", "$0.23", "$0.22"):
        expect(
            section.get_by_text(f"{rate} per call minute", exact=True)
        ).to_be_visible()
    for savings in (4, 8, 12):
        expect(
            section.get_by_text(f"{savings}% lower per-minute rate", exact=True)
        ).to_be_visible()
    expect(section.get_by_role("button", name=re.compile(r"Purchase"))).to_have_count(4)
    expect(section.get_by_text("Best Value", exact=True)).to_have_count(1)


def test_credit_pack_estimates_follow_configured_call_rate(billing_page: Page):
    """Configured voice rates determine both minutes and effective prices."""
    page = billing_page
    setup_credit_products_context(page, voice_credit_cost=20)
    page.get_by_role("tab", name="Credits").click()
    section = page.get_by_test_id("credit-purchase-section")
    for minutes in (10, 25, 50, 100):
        expect(
            section.get_by_text(f"Up to {minutes} call minutes", exact=True)
        ).to_be_visible()
    for rate in ("$0.50", "$0.48", "$0.46", "$0.44"):
        expect(
            section.get_by_text(f"{rate} per call minute", exact=True)
        ).to_be_visible()


def test_credit_pack_missing_rate_does_not_guess_minutes(billing_page: Page):
    """A missing usage rate keeps credit purchases available with per-credit pricing."""
    page = billing_page
    page.route(
        re.compile(r".*/api/v1/billing/credit-events.*"),
        lambda route: route.fulfill(
            status=200, content_type="application/json", body="[]"
        ),
    )
    page.get_by_role("tab", name="Credits").click()
    section = page.get_by_test_id("credit-purchase-section")
    expect(section.get_by_role("button", name=re.compile(r"Purchase"))).to_have_count(4)
    expect(section.get_by_text(re.compile(r"per credit$"))).to_have_count(4)
    expect(section.get_by_text(re.compile(r"Up to .*call minutes"))).to_have_count(0)


def test_credit_pack_checkout_failure_can_retry_without_losing_catalog(
    billing_page: Page,
):
    """A checkout service failure shows recovery guidance and retains the four packs."""
    page = billing_page
    submitted = []

    def fail_checkout(route):
        submitted.append(route.request.post_data_json)
        route.fulfill(
            status=503,
            content_type="application/json",
            body='{"detail":"Checkout temporarily unavailable"}',
        )

    page.route(re.compile(r".*/api/v1/billing/checkout/credits$"), fail_checkout)
    page.get_by_role("tab", name="Credits").click()
    section = page.get_by_test_id("credit-purchase-section")
    expect(section.get_by_text("$0.25 per call minute", exact=True)).to_be_visible()
    section.get_by_role("button", name="Purchase 200", exact=True).click()
    expect(
        page.get_by_text("Failed to start checkout process", exact=True)
    ).to_be_visible()
    assert submitted == [
        {
            "product_id": "20000000-0000-0000-0000-000000000001",
            "organization_id": TEST_ORGANIZATION_ID,
        }
    ]
    for amount in (200, 500, 1000, 2000):
        expect(
            section.get_by_role("button", name=f"Purchase {amount:,}", exact=True)
        ).to_be_enabled()
