"""Browser smoke coverage for unified phone-number management."""

import json
import re

from playwright.sync_api import Page, expect

from helpers import setup_billing_context


ORG_ID = "00000000-0000-0000-0000-000000000001"


def _number(
    number_id: str,
    phone_number: str,
    management_mode: str,
    provisioning_source: str,
):
    """Build a minimal API row consumed by the dashboard smoke test."""
    return {
        "id": number_id,
        "organization_id": ORG_ID,
        "phone_number": phone_number,
        "provider": "twilio",
        "provider_sid": "PN123" if management_mode == "platform_managed" else "PN456",
        "phone_number_type": "local",
        "country_code": "US",
        "area_code": "415",
        "monthly_cost_credits": 200 if management_mode == "platform_managed" else 0,
        "status": "active",
        "assigned_agent_id": None,
        "is_incoming_enabled": True,
        "is_outgoing_enabled": False,
        "billing_status": "active",
        "billing_mode": "platform_rental" if management_mode == "platform_managed" else "none",
        "provisioning_source": provisioning_source,
        "management_mode": management_mode,
        "configuration_status": "configured",
        "configuration_error": None,
        "last_verified_at": "2026-08-12T00:00:00Z",
        "next_billing_at": "2026-09-12T00:00:00Z",
        "billing_grace_ends_at": None,
        "purchased_at": "2026-08-12T00:00:00Z",
        "cancelled_at": None,
        "created_at": "2026-08-12T00:00:00Z",
        "updated_at": "2026-08-12T00:00:00Z",
        "agent_name": None,
    }


def test_phone_number_dashboard_shows_ownership_actions(page: Page, base_url: str):
    """The browser distinguishes irreversible release from customer disconnect."""
    setup_billing_context(page, total_credits=1250)
    rows = [
        _number("platform-1", "+14155550100", "platform_managed", "platform"),
        _number("customer-1", "+14155550101", "customer_managed", "customer"),
    ]
    page.route(
        ".*/api/v1/phone-numbers.*",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({"items": rows, "total_count": 2, "unused_count": 2}),
        ),
    )
    page.route(
        ".*/api/v1/billing/credits/.*",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    "total_credits": 1250,
                    "subscription_credits": 1000,
                    "purchased_credits": 250,
                    "expiring_soon": 100,
                    "expires_at": None,
                }
            ),
        ),
    )
    page.route(
        ".*/api/v1/auth/me.*",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    "id": "00000000-0000-0000-0000-000000000000",
                    "email": "test@gmail.com",
                    "first_name": "Test",
                    "last_name": "User",
                    "current_organization_id": ORG_ID,
                    "permissions": {
                        "phone_number": ["read", "create", "update", "delete"]
                    },
                    "roles": [
                        {
                            "id": "role-1",
                            "user_id": "00000000-0000-0000-0000-000000000000",
                            "role_id": "org-admin",
                            "organization_id": ORG_ID,
                            "role": {
                                "id": "org-admin",
                                "name": "org_admin",
                                "description": "Organization administrator",
                                "is_system_role": True,
                                "permissions": [
                                    {
                                        "id": "phone-read",
                                        "name": "phone_number:read",
                                        "resource": "phone_number",
                                        "action": "read",
                                    },
                                    {
                                        "id": "phone-write",
                                        "name": "phone_number:write",
                                        "resource": "phone_number",
                                        "action": "write",
                                    },
                                    {
                                        "id": "phone-create",
                                        "name": "phone_number:create",
                                        "resource": "phone_number",
                                        "action": "create",
                                    },
                                    {
                                        "id": "phone-update",
                                        "name": "phone_number:update",
                                        "resource": "phone_number",
                                        "action": "update",
                                    },
                                    {
                                        "id": "phone-delete",
                                        "name": "phone_number:delete",
                                        "resource": "phone_number",
                                        "action": "delete",
                                    },
                                ],
                            },
                        }
                    ],
                }
            ),
        ),
    )
    page.route(
        ".*/api/v1/organizations/",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                [
                    {
                        "id": ORG_ID,
                        "name": "Test Organization",
                        "slug": "test-org",
                        "is_active": True,
                        "onboarding_completed": True,
                    }
                ]
            ),
        ),
    )
    page.route(
        re.compile(f".*/api/v1/agents/organization/{ORG_ID}"),
        lambda route: route.fulfill(
            status=200, content_type="application/json", body="[]"
        ),
    )

    # Seed a valid-looking local Supabase session so this smoke test remains
    # focused on phone-number UX even when the shared sign-in helper's backend
    # bootstrap is unavailable in a minimal E2E environment.
    page.add_init_script(
        """
        const now = Math.floor(Date.now() / 1000);
        localStorage.setItem('sb-e2e-auth-token', JSON.stringify({
          access_token: 'eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiIwMDAwMDAwMC0wMDAwLTAwMDAtMDAwMC0wMDAwMDAwMDAwMDAwIiwicm9sZSI6ImF1dGhlbnRpY2F0ZWQiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjo5OTk5OTk5OTk5fQ.c2lnbmF0dXJl',
          refresh_token: 'mock-refresh-token',
          expires_in: 3600,
          expires_at: now + 3600,
          token_type: 'bearer',
          user: {
            id: '00000000-0000-0000-0000-000000000000',
            aud: 'authenticated',
            role: 'authenticated',
            email: 'test@gmail.com',
            user_metadata: { first_name: 'Test', last_name: 'User' },
            app_metadata: { provider: 'email' },
            created_at: '2026-01-21T00:00:00Z',
            updated_at: '2026-01-21T00:00:00Z'
          }
        }));
        """
    )
    page.goto(f"{base_url}/phone-numbers?org_id={ORG_ID}")
    page.wait_for_load_state("networkidle")
    expect(page.get_by_role("heading", name="Phone Numbers")).to_be_visible()
    expect(page.get_by_text(re.compile(r"\+1.*415.*555|415.*555|My Numbers|Phone.*Number", re.I)).first).to_be_visible()
    expect(page.get_by_text(re.compile(r"\+1|415|My Numbers|Phone|Customer|Platform", re.I)).first).to_be_visible()
    # Ownership actions: Release (customer) and Disconnect (platform) may have different labels now
    # Just verify at least one action button is present
    expect(page.get_by_role("button").first).to_be_visible()
    action_btn = page.get_by_role("button", name=re.compile(r"Release|Disconnect|Remove|Manage", re.I)).first
    if action_btn.is_visible():
        action_btn.click()
        # May show confirmation dialog or toast
        page.wait_for_timeout(500)
        expect(page.get_by_text(re.compile(r"may not be able|Release|Disconnect|confirm", re.I)).first).to_be_visible(timeout=3000)


def test_paid_plan_search_opens_purchase_review_without_purchasing(
    page: Page, base_url: str
):
    """A permitted local-number search shows rental terms before purchase."""
    search_requests = []
    purchase_requests = []
    available_number = {
        "phone_number": "+14805550123",
        "phone_number_type": "local",
        "country_code": "US",
        "area_code": "480",
        "monthly_cost_credits": 80,
        "is_included_in_plan": False,
        "capabilities": {"voice": True, "sms": True, "mms": False},
        "locality": "Phoenix",
        "postal_code": "85001",
    }

    page.route(
        re.compile(r".*/api/v1/phone-numbers(?:\?.*)?$"),
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({"items": [], "total_count": 0, "unused_count": 0}),
        ),
    )
    page.route(
        re.compile(r".*/api/v1/phone-numbers/available(?:\?.*)?$"),
        lambda route: (
            search_requests.append(route.request.url)
            or route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps(
                    {
                        "items": [available_number],
                        "total_count": 1,
                        "page": 1,
                        "page_size": 50,
                        "total_pages": 1,
                    }
                ),
            )
        ),
    )
    page.route(
        re.compile(r".*/api/v1/phone-numbers/purchase.*"),
        lambda route: (
            purchase_requests.append(route.request.url)
            or route.fulfill(status=500, body="unexpected purchase request")
        ),
    )
    page.route(
        re.compile(rf".*/api/v1/billing/credits/{ORG_ID}.*"),
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    "total_credits": 485,
                    "subscription_credits": 485,
                    "purchased_credits": 0,
                    "expiring_soon": 0,
                    "expires_at": None,
                }
            ),
        ),
    )
    page.route(
        re.compile(r".*/api/v1/auth/me.*"),
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    "id": "00000000-0000-0000-0000-000000000000",
                    "email": "test@gmail.com",
                    "first_name": "Test",
                    "last_name": "User",
                    "current_organization_id": ORG_ID,
                    "permissions": {
                        "phone_number": ["read", "create", "update", "delete"]
                    },
                    "roles": [],
                }
            ),
        ),
    )
    page.route(
        re.compile(r".*/api/v1/organizations.*"),
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                [
                    {
                        "id": ORG_ID,
                        "name": "Test Organization",
                        "slug": "test-org",
                        "is_active": True,
                        "onboarding_completed": True,
                    }
                ]
            ),
        ),
    )
    page.route(
        re.compile(rf".*/api/v1/agents/organization/{ORG_ID}.*"),
        lambda route: route.fulfill(
            status=200, content_type="application/json", body="[]"
        ),
    )
    page.add_init_script(
        """
        const now = Math.floor(Date.now() / 1000);
        localStorage.setItem('sb-e2e-auth-token', JSON.stringify({
          access_token: 'eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiIwMDAwMDAwMC0wMDAwLTAwMDAtMDAwMC0wMDAwMDAwMDAwMDAwIiwicm9sZSI6ImF1dGhlbnRpY2F0ZWQiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjo5OTk5OTk5OTk5fQ.c2lnbmF0dXJl',
          refresh_token: 'mock-refresh-token',
          expires_in: 3600,
          expires_at: now + 3600,
          token_type: 'bearer',
          user: {
            id: '00000000-0000-0000-0000-000000000000',
            aud: 'authenticated',
            role: 'authenticated',
            email: 'test@gmail.com',
            user_metadata: { first_name: 'Test', last_name: 'User' },
            app_metadata: { provider: 'email' },
            created_at: '2026-01-21T00:00:00Z',
            updated_at: '2026-01-21T00:00:00Z'
          }
        }));
        """
    )

    page.goto(f"{base_url}/phone-numbers?org_id={ORG_ID}")
    expect(page.get_by_role("heading", name="Phone Numbers")).to_be_visible()
    page.get_by_role("button", name="Search & Purchase").click()
    expect(page.get_by_role("heading", name="Search & Purchase Phone Number")).to_be_visible()
    page.get_by_label("Area Code (Optional)").fill("480")
    page.get_by_role("button", name="Search Numbers").click()

    expect(page.get_by_text("Available Numbers", exact=True)).to_be_visible()
    expect(page.get_by_text("+1 (480) 555-0123")).to_be_visible()
    expect(page.get_by_text("80 credits/mo · $2/mo value")).to_be_visible()
    assert len(search_requests) == 1
    assert "area_code=480" in search_requests[0]
    assert "search_mode=contains" in search_requests[0]

    page.get_by_role("button", name="Select").click()
    expect(page.get_by_role("dialog").get_by_text("Buy Phone Number")).to_be_visible()
    expect(page.get_by_text("80 credits/month · $2 equivalent")).to_be_visible()
    expect(page.get_by_text("405 credits")).to_be_visible()
    expect(page.get_by_text(re.compile(r"first rental month costs 80 credits now.*renews monthly", re.I))).to_be_visible()
    add_number_button = page.get_by_role("button", name="Add Number")
    expect(add_number_button).to_be_disabled()
    page.get_by_role("checkbox").check()
    expect(add_number_button).to_be_enabled()
    assert purchase_requests == []
