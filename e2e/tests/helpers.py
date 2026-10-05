"""Helper functions for E2E test context setup."""
import re
import pytest
from playwright.sync_api import Page, expect


def signin_user(page: Page, base_url: str, wait_for_dashboard: bool = True):
    """Helper to sign in with test credentials.
    
    This function handles the standard sign-in flow used across multiple tests,
    ensuring consistent authentication behavior and reducing code duplication.
    
    Args:
        page: Playwright Page instance to perform sign-in on
        base_url: Base URL of the application (e.g., http://localhost:3001)
        wait_for_dashboard: Whether to wait for Dashboard heading after sign-in (default: True)
            Set to False for tests that test the sign-in flow itself
    
    Example:
        ```python
        signin_user(page, base_url)
        # Continue with test...
        ```
    """
    page.goto(f"{base_url}/auth/signin")
    page.fill('input#email', "test@gmail.com")
    page.fill('input#password', "Password123!")
    page.click('button[type="submit"]')
    
    if wait_for_dashboard:
        expect(page).to_have_url(re.compile(r".*/dashboard(?:\?.*)?$"), timeout=10000)


def setup_billing_context(page, total_credits: int = 1250):
    """Setup billing context for tests requiring credit balance verification.
    
    This function mocks the billing balance API to return a specific credit balance,
    ensuring that billing-related UI components are properly hydrated during tests.
    
    Args:
        page: Playwright Page instance to apply mocks to
        total_credits: Total number of credits to mock (default: 1250)
    
    Example:
        ```python
        setup_billing_context(page, total_credits=1250)
        ```
    """
    subscription_credits = max(1000, int(total_credits * 0.8))
    purchased_credits = max(250, total_credits - subscription_credits)
    expiring_soon = max(100, int(total_credits * 0.08))
    
    page.route(re.compile(r".*/api/v1/billing/balance"), lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=f'''{{
            "total_credits": {total_credits},
            "subscription_credits": {subscription_credits},
            "purchased_credits": {purchased_credits},
            "expiring_soon": {expiring_soon},
            "expires_at": null
        }}'''
    ))


def setup_billing_plans_context(page):
    """Setup billing plans context for tests requiring plan display verification.
    
    This function mocks the billing plans API to return sample subscription plans,
    ensuring that plan selection UI components are properly hydrated during tests.
    
    Args:
        page: Playwright Page instance to apply mocks to
    
    Example:
        ```python
        setup_billing_plans_context(page)
        ```
    """
    page.route(re.compile(r".*/api/v1/billing/plans.*"), lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body='''[
            {
                "id": "plan-pro",
                "name": "Professional Plan",
                "description": "For growing businesses",
                "stripe_price_id": "price_pro",
                "stripe_product_id": "prod_pro",
                "price_amount": 4900,
                "currency": "USD",
                "interval": "monthly",
                "interval_count": 1,
                "included_credits": 5000,
                "max_users": 10,
                "features": {"agents": 10, "credits": 5000},
                "entitlements": {"agents": 10, "credits": 5000},
                "entitlement_metadata": {},
                "is_active": true,
                "trial_period_days": null,
                "created_at": "2026-01-21T00:00:00Z",
                "updated_at": "2026-01-21T00:00:00Z"
            }
        ]'''
    ))


def setup_credit_products_context(page, organization_id: str = "test-org-id"):
    """Setup credit products context for tests requiring credit purchase options.
    
    This function mocks the credit products API to return sample credit packages,
    ensuring that credit purchase UI components are properly hydrated during tests.
    
    Args:
        page: Playwright Page instance to apply mocks to
    
    Example:
        ```python
        setup_credit_products_context(page)
        ```
    """
    page.route(
        re.compile(r".*/api/v1/billing/entitlements/.*"),
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=f'''{{
                "organization_id": "{organization_id}",
                "plan_version_id": "test-plan-version",
                "plan_product_slug": "pro",
                "plan_version_number": 1,
                "plan_version_label": "Pro",
                "is_legacy_version": false,
                "is_entitled": true,
                "cancel_at_period_end": false,
                "access_until": null,
                "limits": {{}},
                "features": {{
                    "credit_topup_enabled": {{
                        "key": "credit_topup_enabled",
                        "kind": "feature",
                        "assigned": true,
                        "raw_value": null,
                        "effective_value": true,
                        "is_unlimited": false
                    }}
                }},
                "migration": null
            }}''',
        ),
    )
    page.route(re.compile(r".*/api/v1/billing/credit-products.*"), lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body='''[
            {
                "name": "200 Credits Pack",
                "description": "200 credits for small usage",
                "stripe_price_id": "price_test_200_credits",
                "stripe_product_id": "prod_test_200_credits",
                "credit_amount": 200,
                "price_amount": 500,
                "currency": "USD",
                "is_active": true,
                "id": "20000000-0000-0000-0000-000000000001",
                "created_at": "2026-10-02T00:00:00Z",
                "updated_at": "2026-10-02T00:00:00Z"
            },
            {
                "name": "400 Credits Pack",
                "description": "400 credits for regular usage",
                "stripe_price_id": "price_test_400_credits",
                "stripe_product_id": "prod_test_400_credits",
                "credit_amount": 400,
                "price_amount": 1000,
                "currency": "USD",
                "is_active": true,
                "id": "40000000-0000-0000-0000-000000000001",
                "created_at": "2026-10-02T00:00:00Z",
                "updated_at": "2026-10-02T00:00:00Z"
            },
            {
                "name": "1000 Credits Pack",
                "description": "1000 credits for heavy usage",
                "stripe_price_id": "price_test_1000_credits",
                "stripe_product_id": "prod_test_1000_credits",
                "credit_amount": 1000,
                "price_amount": 2500,
                "currency": "USD",
                "is_active": true,
                "id": "10000000-0000-0000-0000-000000000001",
                "created_at": "2026-10-02T00:00:00Z",
                "updated_at": "2026-10-02T00:00:00Z"
            }
        ]'''
    ))
