"""Browser smoke coverage for the consolidated platform plan catalog."""

import json
import re

from playwright.sync_api import Page, expect



def test_usage_pricing_tab_is_deep_linkable_and_explains_system_rates(
    page: Page, base_url: str, step
):
    """Platform admins can land directly on usage pricing and inspect its rules."""
    events = [
        (
            "voice_call_minute",
            "Voice calls are charged for each connected whole minute.",
            10,
        ),
        (
            "phone_number_local_month",
            "An active local phone number is charged once for each rental month.",
            200,
        ),
        (
            "phone_number_mobile_month",
            "An active mobile phone number is charged once for each rental month.",
            200,
        ),
        (
            "phone_number_toll_free_month",
            "An active toll-free phone number is charged once for each rental month.",
            500,
        ),
    ]
    body = [
        {
            "id": f"00000000-0000-0000-0000-{index:012d}",
            "name": name,
            "description": description,
            "credit_cost": cost,
            "category": "voice" if name.startswith("voice") else "phone_number",
            "is_active": True,
            "meter_type": "duration" if name.startswith("voice") else "count",
            "billing_unit": "minute" if name.startswith("voice") else "month",
            "created_at": "2026-01-21T00:00:00Z",
            "updated_at": "2026-01-21T00:00:00Z",
        }
        for index, (name, description, cost) in enumerate(events, start=1)
    ]
    page.route(
        "**/api/v1/admin/credit-events",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(body),
        ),
    )
    page.route(
        "**/api/v1/organizations/",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body='[{"id":"00000000-0000-0000-0000-000000000001","name":"Test Organization","slug":"test-org","is_active":true,"onboarding_completed":true}]',
        ),
    )

    # Seed the same local Supabase session shape used by the application. This
    # keeps the smoke focused on the catalog route while the existing autouse
    # fixture continues to mock the backend profile boundary.
    page.add_init_script(
        """
        const now = Math.floor(Date.now() / 1000);
        localStorage.setItem('sb-gdzwiwukcwbqohfwxxrx-auth-token', JSON.stringify({
          access_token: 'eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiIwMDAwMDAwMC0wMDAwLTAwMDAtMDAwMC0wMDAwMDAwMDAwMDAwIiwicm9sZSI6ImF1dGhlbnRpY2F0ZWQiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjo5OTk5OTk5OTk5fQ.signature',
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

    step("Open the deep-linked usage pricing tab as a platform administrator")

    step("Open the deep-linked usage pricing tab")
    page.goto(f"{base_url}/platform/plans?tab=usage")
    page.wait_for_load_state("networkidle")

    expect(page).to_have_url(re.compile(r"/platform/plans\?tab=usage$"))
    expect(page.get_by_role("heading", name="Plan Catalog")).to_be_visible()
    expect(page.get_by_role("table", name="System usage pricing")).to_be_visible()
    expect(page.get_by_text("Voice calls", exact=True)).to_be_visible()
    expect(page.get_by_text("Local phone numbers", exact=True)).to_be_visible()
    expect(page.get_by_text("Mobile phone numbers", exact=True)).to_be_visible()
    expect(page.get_by_text("Toll-free phone numbers", exact=True)).to_be_visible()

    step("Inspect the explanation for voice-minute pricing")
    page.get_by_role(
        "button", name="More information about Voice calls"
    ).hover()
    expect(
        page.get_by_role(
            "tooltip", name="Voice calls are charged for each connected whole minute."
        )
    ).to_be_visible()
