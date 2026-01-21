import re
from playwright.sync_api import Page, expect
from helpers import signin_user


def test_full_onboarding_journey(page: Page, base_url: str, step):
    """
    Test complete onboarding journey for first-time authenticated users.

    Purpose:
        Verify that users without organizations are redirected to organization creation
        and can successfully create their first organization, then access the dashboard.

    Test Specification:
        1. Mock organizations API to initially return empty list (no organizations exist)
        2. Sign in with valid test credentials (platform_admin role)
        3. Verify automatic redirection to organization creation page (/create-organization)
        4. Mock organization creation API to return success
        5. Update organizations mock to return newly created organization
        6. Fill organization form with valid data (name, slug)
        7. Submit organization creation form
        8. Verify redirection to dashboard after successful creation
        9. Verify Dashboard heading is visible

    Mocks Required:
        - /api/v1/organizations (initial: empty list, after creation: returns new org)
        - /api/v1/organizations/self (creation endpoint, returns 201)

    Expected Behavior:
        - After sign-in, user is automatically redirected to /create-organization
        - Organization form displays correctly
        - Upon submission, organization is created successfully
        - User is redirected to /dashboard after creation
        - Dashboard heading "Dashboard" is visible

    Dependencies:
        - User must have platform_admin role (mocked)
        - Sign-in helper (does not wait for dashboard, allows onboarding flow)
    """

    # Override organizations API to return no organizations initially
    step("Setup: Mock organizations API to return no organizations initially")
    organizations_returned = []
    def handle_organizations(route):
        route.fulfill(
            status=200,
            content_type="application/json",
            body=str(organizations_returned).replace("'", '"').replace("True", "true")
        )

    page.route("**/api/v1/organizations", handle_organizations)

    step("Sign in with existing test credentials")
    signin_user(page, base_url, wait_for_dashboard=False)

    # Since user has platform_admin role but no organizations,
    # OrganizationCheck should redirect to organization creation
    step("Verify redirection to Organization Creation page")
    expect(page).to_have_url(re.compile(r".*/create-organization"), timeout=10000)

    # Now update the organizations mock to return the created organization
    step("Update organizations mock to return created organization")
    # Mock organization creation API
    page.route("**/api/v1/organizations/self", lambda route: route.fulfill(
        status=201,
        content_type="application/json",
        body='{"id": "test-org-id", "name": "Test Organization", "slug": "test-org", "is_active": true}'
    ))
    # Update the organizations list to include the new organization
    organizations_returned.append({
        "id": "test-org-id",
        "name": "Test Organization",
        "slug": "test-org",
        "is_active": True
    })

    step("Create a test organization")
    page.fill('input#name', "Test Organization")
    page.fill('input#slug', "test-organization")
    page.click('button[type="submit"]')

    # After creating organization, should be redirected to dashboard
    step("Wait for organization creation and redirection")
    page.wait_for_timeout(3000)  # Give time for async operations
    step("Verify final redirection to Dashboard")
    expect(page).to_have_url(re.compile(r".*/dashboard"), timeout=15000)
    expect(page.get_by_role("heading", name=re.compile(r"Dashboard", re.I))).to_be_visible(timeout=10000)

def test_signin_validation_journey(page: Page, base_url: str, step):
    """
    Test sign-in form validation and error handling for invalid credentials.

    Purpose:
        Verify that the sign-in form properly validates input and displays appropriate
        error messages when invalid credentials are submitted.

    Test Specification:
        1. Mock sign-in token API to return authentication failure (401)
        2. Navigate to sign-in page
        3. Submit form with invalid email and password
        4. Verify error alert is displayed with authentication failure message

    Mocks Required:
        - /auth/v1/token** (returns 401 with invalid_grant error)

    Expected Behavior:
        - Sign-in form accepts input submission
        - Error alert is displayed upon authentication failure
        - Error message indicates invalid credentials or authentication failure

    Dependencies:
        - None (tests sign-in page behavior directly)
    """

    step("Setup: Override signin mock to fail")
    page.route("**/auth/v1/token**", lambda route: route.fulfill(
        status=401,
        content_type="application/json",
        body='{"error": "invalid_grant", "error_description": "Invalid login credentials"}'
    ))

    step("Navigate to Signin page")
    page.goto(f"{base_url}/auth/signin")

    step("Submit invalid credentials")
    page.fill('input#email', "wrong@example.com")
    page.fill('input#password', "wrongpassword")
    page.click('button[type="submit"]')

    step("Verify error alert is shown")
    expect(page.locator('div[role="alert"]').get_by_text(re.compile(r"invalid|failed|error|credentials", re.I))).to_be_visible()

