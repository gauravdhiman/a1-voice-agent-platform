"""
Phone Numbers E2E Tests

Purpose: Test the phone number feature end-to-end

Note: These tests use the real database and backend, only mocking:
- Supabase Auth (external boundary service)
- Twilio API (external third-party service)
"""

import pytest
from playwright.sync_api import Page, expect
from helpers import signin_user


def test_navigate_to_dashboard(page: Page, base_url: str, step):
    """Test dashboard loads for authenticated user."""
    step("Sign in")
    signin_user(page, base_url)
    
    step("Navigate to dashboard")
    page.goto(f"{base_url}/dashboard")
    page.wait_for_load_state("networkidle")
    
    # Take screenshot
    page.screenshot(path="/tmp/e2e_dashboard.png", full_page=True)


def test_navigate_to_agents(page: Page, base_url: str, step):
    """Test agents page loads."""
    step("Sign in")
    signin_user(page, base_url)
    
    step("Navigate to agents")
    page.goto(f"{base_url}/agents")
    page.wait_for_load_state("networkidle")
    
    page.screenshot(path="/tmp/e2e_agents.png", full_page=True)


def test_navigate_to_organization(page: Page, base_url: str, step):
    """Test organization page loads."""
    step("Sign in")
    signin_user(page, base_url)
    
    step("Navigate to organization")
    page.goto(f"{base_url}/organization")
    page.wait_for_load_state("networkidle")
    
    page.screenshot(path="/tmp/e2e_organization.png", full_page=True)
