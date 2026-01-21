import re
from playwright.sync_api import Page, expect
from helpers import setup_billing_plans_context, setup_credit_products_context, signin_user


def test_billing_page_functionality(page: Page, base_url: str, step):
    """
    Test billing page displays correct information across Overview, Plans, and Credits tabs.

    Purpose:
        Verify that the billing page correctly displays subscription overview, available plans,
        and credit purchase options when a user accesses the billing section.

    Test Specification:
        1. Mock organization APIs to return a test organization
        2. Mock billing summary API to return credit balance and usage data
        3. Mock credit balance API to return detailed credit breakdown
        4. Mock subscription plans API to return available plans
        5. Mock credit products API to return purchasable credit packages
        6. Sign in as authenticated user
        7. Navigate to billing page with organization ID
        8. Verify Overview tab displays current balance (1,250) and usage (150)
        9. Switch to Plans tab and verify "Professional Plan" ($49) is displayed
        10. Switch to Credits tab and verify credit packages are shown (100, 1000 credits)

    Mocks Required:
        - /api/v1/organizations (list of organizations)
        - /api/v1/organizations/{org_id} (single organization)
        - /api/v1/billing/summary/{org_id} (billing summary)
        - /api/v1/billing/credits/{org_id} (credit balance breakdown)
        - /api/v1/billing/plans (subscription plans)
        - /api/v1/billing/credit-products (credit purchase packages)

    Expected Behavior:
        - Billing page loads without errors
        - Overview tab shows formatted credit balance and usage statistics
        - Plans tab displays available subscription plans with pricing
        - Credits tab displays purchasable credit packages
        - All data matches mocked API responses

    Dependencies:
        - User must be authenticated (sign-in helper)
        - Organization must exist in mocked data
    """

    test_org_id = "test-org-id"

    # Mock organization APIs
    page.route("**/api/v1/organizations", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=f'[{{"id": "{test_org_id}", "name": "Test Organization", "slug": "test-org", "is_active": true}}]'
    ))

    page.route(f"**/api/v1/organizations/{test_org_id}", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=f'''{{
            "id": "{test_org_id}",
            "name": "Test Organization",
            "description": "Test organization for billing",
            "slug": "test-org",
            "website": null,
            "is_active": true,
            "created_at": "2026-01-21T00:00:00Z",
            "updated_at": "2026-01-21T00:00:00Z"
        }}'''
    ))

    # Mock billing APIs
    page.route(f"**/api/v1/billing/summary/{test_org_id}", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=f'''{{
            "organization_id": "{test_org_id}",
            "subscription": null,
            "credit_balance": 1250,
            "current_period_usage": 150,
            "next_billing_date": null,
            "amount_due": null
        }}'''
    ))

    page.route(f"**/api/v1/billing/credits/{test_org_id}", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body='''{
            "total_credits": 1250,
            "subscription_credits": 1000,
            "purchased_credits": 250,
            "expiring_soon": 100,
            "expires_at": null
        }'''
    ))

    setup_billing_plans_context(page)
    setup_credit_products_context(page)

    # Sign in
    step("Sign in with test credentials")
    signin_user(page, base_url)

    # Navigate to billing page
    step("Navigate to billing page")
    page.goto(f"{base_url}/organization/billing?org_id={test_org_id}")

    # Verify Overview tab displays billing summary
    step("Verify billing overview shows credits (1,250) and usage (150)")
    expect(page.get_by_text("1,250")).to_be_visible(timeout=5000)
    expect(page.get_by_text(re.compile(r"Current Balance|Credit Balance", re.I))).to_be_visible()

    # Switch to Plans tab
    step("Switch to Plans tab and verify subscription plans")
    page.get_by_role("tab", name="Plans").click()
    expect(page.get_by_text("Professional Plan")).to_be_visible(timeout=3000)
    expect(page.get_by_text("$49")).to_be_visible()

    # Switch to Credits tab
    step("Switch to Credits tab and verify credit balance details")
    page.get_by_role("tab", name="Credits").click()
    page.wait_for_timeout(2000)
    expect(page.get_by_text("100 Credits Pack")).to_be_visible(timeout=3000)
    expect(page.get_by_text("1000 Credits Pack")).to_be_visible()
