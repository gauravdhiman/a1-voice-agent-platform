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
        expect(page.get_by_role("heading", name=re.compile(r"Dashboard", re.I))).to_be_visible(timeout=10000)


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
    
    page.route("**/api/v1/billing/balance", lambda route: route.fulfill(
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
    page.route("**/api/v1/billing/plans**", lambda route: route.fulfill(
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
                "is_active": true,
                "trial_period_days": null,
                "created_at": "2026-01-21T00:00:00Z",
                "updated_at": "2026-01-21T00:00:00Z"
            }
        ]'''
    ))


def setup_credit_products_context(page):
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
    page.route("**/api/v1/billing/credit-products?*", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body='''[
            {
                "name": "100 Credits Pack",
                "description": "100 credits for small usage",
                "stripe_price_id": "price_1S8TBKDCTx1JlMd8qVCd2C3z",
                "stripe_product_id": "prod_T4cQgYdUHvaUDo",
                "credit_amount": 100,
                "price_amount": 1500,
                "currency": "USD",
                "is_active": true,
                "id": "462ddaab-a189-469c-b325-c5d89fa4627c",
                "created_at": "2025-10-02T05:59:18.070927Z",
                "updated_at": "2025-10-02T05:59:18.070927Z"
            },
            {
                "name": "1000 Credits Pack",
                "description": "1000 credits for regular usage",
                "stripe_price_id": "price_1S8TBKDCTx1JlMd8QhI5MZjY",
                "stripe_product_id": "prod_T4cQFSfYo14Chr",
                "credit_amount": 1000,
                "price_amount": 2500,
                "currency": "USD",
                "is_active": true,
                "id": "6575d8a0-a1d4-4d7b-b821-5e8710cbd5f5",
                "created_at": "2025-10-02T05:59:17.855402Z",
                "updated_at": "2025-10-02T05:59:17.855402Z"
            }
        ]'''
    ))
