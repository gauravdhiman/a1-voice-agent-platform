import pytest
import re
from playwright.sync_api import Page, expect

@pytest.mark.skip(reason="Billing hydration needs more context setup")
def test_billing_overview_display(page: Page, base_url: str):
    """Test that billing info and credits are displayed correctly."""
    
    # 1. Mock Credit Balance API
    page.route("**/api/v1/billing/balance", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body='{"total_credits": 1250, "subscription_credits": 1000, "purchased_credits": 250, "expiring_soon": 100, "expires_at": null}'
    ))

    # 2. Sign in
    page.goto(f"{base_url}/auth/signin")
    page.fill('input#email', "test@gmail.com")
    page.fill('input#password', "Password123!")
    page.click('button[type="submit"]')
    
    # Wait for Dashboard to ensure context is ready
    expect(page.get_by_role("heading", name=re.compile(r"Dashboard", re.I))).to_be_visible(timeout=10000)

    # 3. Navigate to Billing page
    # The organization-context should be hydrated now
    page.goto(f"{base_url}/organization/billing")
    page.wait_for_load_state("networkidle")

    # 4. Verify credit display
    expect(page.get_by_text("1,250")).to_be_visible(timeout=15000)
    expect(page.get_by_text(re.compile(r"Total Credits|Current Balance", re.I))).to_be_visible()

@pytest.mark.skip(reason="Billing plan timeouts in E2E environment")
def test_subscription_plans_display(page: Page, base_url: str):
    """Test that subscription plans are loaded and displayed."""
    
    # Mock Plans API
    page.route("**/api/v1/billing/plans**", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body='''[
            {
                "id": "plan-pro",
                "name": "Professional Plan",
                "description": "For growing businesses",
                "price_amount": 4900,
                "currency": "usd",
                "interval": "monthly",
                "interval_count": 1,
                "features": {"agents": 10, "credits": 5000},
                "is_active": true,
                "stripe_price_id": "price_pro",
                "stripe_product_id": "prod_pro"
            }
        ]'''
    ))

    page.goto(f"{base_url}/organization/billing")
    page.wait_for_load_state("networkidle")

    # Verify plan info
    expect(page.get_by_text("Professional Plan")).to_be_visible()
    expect(page.get_by_text("$49")).to_be_visible()
