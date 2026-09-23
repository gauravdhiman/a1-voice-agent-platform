/**
 * Tests for the <PhoneNumberDashboard> component (N1 #2 — write-action gate).
 *
 * Contract (mirrors the N1 follow-up #1 memory + user feedback "actions
 * like deleting a skill ... should respect the permissions of the
 * user's role"):
 *   - The dashboard accepts a `canManage?: boolean` prop, default `true`
 *     for back-compat with pre-N1 call sites.
 *   - When `canManage` is true: all four write buttons render —
 *     "Search & Purchase" and "Connect Existing" actions
 *     (with numbers), per-row "Assign", per-row "Release" or "Disconnect".
 *   - When `canManage` is false: NONE of the write buttons render.
 *     The list still shows, but is read-only.
 *
 * This is the component-level test. The page-level test
 * (src/app/(dashboard)/phone-numbers/__tests__/page.test.tsx)
 * verifies the page passes the prop correctly.
 */
import React from "react";
import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { PhoneNumberWithAgent } from "@/types/phone-number";

// Stub the dialog + sheet children — we just want to assert button
// presence/absence at the dashboard level. The dialogs themselves have
// their own concerns.
vi.mock("@/components/phone-numbers/phone-number-assign-dialog", () => ({
  PhoneNumberAssignDialog: () => null,
}));

vi.mock("@/components/phone-numbers/phone-number-cancel-dialog", () => ({
  PhoneNumberCancelDialog: () => null,
}));

vi.mock("@/components/phone-numbers/phone-number-purchase", () => ({
  PhoneNumberPurchase: () => null,
}));

vi.mock("@/components/phone-numbers/phone-number-search", () => ({
  PhoneNumberSearch: () => null,
}));

import { PhoneNumberDashboard } from "../phone-number-dashboard";

const FIXTURE_NUMBERS: PhoneNumberWithAgent[] = [
  {
    id: "pn-1",
    phone_number: "+15555550100",
    phone_number_type: "local",
    country_code: "US",
    area_code: "555",
    provider: "twilio",
    provider_sid: "PN123",
    status: "active",
    assigned_agent_id: null,
    agent_name: null,
    monthly_cost_credits: 100,
    is_incoming_enabled: true,
    is_outgoing_enabled: true,
    billing_status: "active",
    billing_mode: "platform_rental",
    provisioning_source: "platform",
    management_mode: "platform_managed",
    configuration_status: "configured",
    configuration_error: null,
    last_verified_at: null,
    next_billing_at: null,
    billing_grace_ends_at: null,
    organization_id: "org-1",
    purchased_at: "2024-01-01T00:00:00Z",
    cancelled_at: null,
    created_at: "2024-01-01T00:00:00Z",
    updated_at: "2024-01-01T00:00:00Z",
  },
];

const CUSTOMER_NUMBER: PhoneNumberWithAgent = {
  ...FIXTURE_NUMBERS[0],
  id: "pn-customer",
  phone_number: "+15555550101",
  monthly_cost_credits: 0,
  billing_mode: "none",
  provisioning_source: "customer",
  management_mode: "customer_managed",
};

const CUSTOMER_VERIFICATION_NUMBER: PhoneNumberWithAgent = {
  ...CUSTOMER_NUMBER,
  status: "verification_required",
};

describe("<PhoneNumberDashboard> (N1 #2 — write-action gate)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("renders purchase and connect actions by default", () => {
    render(
      <PhoneNumberDashboard
        organizationId="org-1"
        phoneNumbers={[]}
        isLoading={false}
      />,
    );

    expect(
      screen.getByRole("button", { name: /search & purchase/i }),
    ).toBeInTheDocument();
  });

  it("hides empty-state phone actions when canManage is false", () => {
    render(
      <PhoneNumberDashboard
        organizationId="org-1"
        phoneNumbers={[]}
        isLoading={false}
        canManage={false}
      />,
    );

    expect(
      screen.queryByRole("button", { name: /search & purchase/i }),
    ).not.toBeInTheDocument();
  });

  it("renders phone management actions when canManage is true (with numbers)", () => {
    render(
      <PhoneNumberDashboard
        organizationId="org-1"
        phoneNumbers={FIXTURE_NUMBERS}
        isLoading={false}
        canManage
      />,
    );

    expect(
      screen.getByRole("button", { name: /connect existing/i }),
    ).toBeInTheDocument();
  });

  it("hides connect action when canManage is false", () => {
    render(
      <PhoneNumberDashboard
        organizationId="org-1"
        phoneNumbers={FIXTURE_NUMBERS}
        isLoading={false}
        canManage={false}
      />,
    );

    expect(
      screen.queryByRole("button", { name: /connect existing/i }),
    ).not.toBeInTheDocument();
  });

  it("renders the per-row 'Assign' and 'Release' buttons when canManage is true", () => {
    render(
      <PhoneNumberDashboard
        organizationId="org-1"
        phoneNumbers={FIXTURE_NUMBERS}
        isLoading={false}
        canManage
      />,
    );

    expect(
      screen.getByRole("button", { name: /^assign$/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /^release$/i }),
    ).toBeInTheDocument();
  });

  it("keeps each phone number card clipped to its responsive surface", () => {
    render(
      <PhoneNumberDashboard
        organizationId="org-1"
        phoneNumbers={FIXTURE_NUMBERS}
        isLoading={false}
        canManage
      />,
    );

    expect(screen.getByTestId("phone-number-card").className).toContain(
      "overflow-hidden",
    );
  });

  it("uses Disconnect for customer-owned numbers", () => {
    render(
      <PhoneNumberDashboard
        organizationId="org-1"
        phoneNumbers={[CUSTOMER_NUMBER]}
        isLoading={false}
        canManage
      />,
    );

    expect(
      screen.getByRole("button", { name: /^disconnect$/i }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /^release$/i }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /view setup details/i }),
    ).not.toBeInTheDocument();
  });

  it("shows setup details only while a customer number awaits verification", () => {
    render(
      <PhoneNumberDashboard
        organizationId="org-1"
        phoneNumbers={[CUSTOMER_VERIFICATION_NUMBER]}
        isLoading={false}
        canManage
      />,
    );

    expect(
      screen.getByRole("button", { name: /view setup details/i }),
    ).toBeInTheDocument();
  });

  it("hides per-row actions when canManage is false (CRIT — read-only user)", () => {
    render(
      <PhoneNumberDashboard
        organizationId="org-1"
        phoneNumbers={FIXTURE_NUMBERS}
        isLoading={false}
        canManage={false}
      />,
    );

    expect(
      screen.queryByRole("button", { name: /^assign$/i }),
      "regular member must not see the per-row Assign button",
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /^release$/i }),
      "regular member must not see the per-row Cancel button",
    ).not.toBeInTheDocument();
  });
});
