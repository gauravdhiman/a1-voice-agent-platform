/**
 * Tests for the <PhoneNumberDashboard> component (N1 #2 — write-action gate).
 *
 * Contract (mirrors the N1 follow-up #1 memory + user feedback "actions
 * like deleting a skill ... should respect the permissions of the
 * user's role"):
 *   - The dashboard accepts a `canManage?: boolean` prop, default `true`
 *     for back-compat with pre-N1 call sites.
 *   - When `canManage` is true: all four write buttons render —
 *     "Search & Purchase Phone Number" (empty state), "Add Phone Number"
 *     (with numbers), per-row "Assign", per-row "Cancel".
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
    organization_id: "org-1",
    purchased_at: "2024-01-01T00:00:00Z",
    cancelled_at: null,
    created_at: "2024-01-01T00:00:00Z",
    updated_at: "2024-01-01T00:00:00Z",
  },
];

describe("<PhoneNumberDashboard> (N1 #2 — write-action gate)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("renders the empty-state 'Search & Purchase' button by default (canManage defaults to true)", () => {
    render(
      <PhoneNumberDashboard
        organizationId="org-1"
        phoneNumbers={[]}
        isLoading={false}
      />,
    );

    expect(
      screen.getByRole("button", { name: /search & purchase phone number/i }),
    ).toBeInTheDocument();
  });

  it("hides the empty-state 'Search & Purchase' button when canManage is false", () => {
    render(
      <PhoneNumberDashboard
        organizationId="org-1"
        phoneNumbers={[]}
        isLoading={false}
        canManage={false}
      />,
    );

    expect(
      screen.queryByRole("button", { name: /search & purchase phone number/i }),
    ).not.toBeInTheDocument();
  });

  it("renders the 'Add Phone Number' button when canManage is true (with numbers)", () => {
    render(
      <PhoneNumberDashboard
        organizationId="org-1"
        phoneNumbers={FIXTURE_NUMBERS}
        isLoading={false}
        canManage
      />,
    );

    expect(
      screen.getByRole("button", { name: /add phone number/i }),
    ).toBeInTheDocument();
  });

  it("hides the 'Add Phone Number' button when canManage is false", () => {
    render(
      <PhoneNumberDashboard
        organizationId="org-1"
        phoneNumbers={FIXTURE_NUMBERS}
        isLoading={false}
        canManage={false}
      />,
    );

    expect(
      screen.queryByRole("button", { name: /add phone number/i }),
    ).not.toBeInTheDocument();
  });

  it("renders the per-row 'Assign' and 'Cancel' buttons when canManage is true", () => {
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
      screen.getByRole("button", { name: /^cancel$/i }),
    ).toBeInTheDocument();
  });

  it("hides per-row 'Assign' and 'Cancel' buttons when canManage is false (CRIT — read-only user)", () => {
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
      screen.queryByRole("button", { name: /^cancel$/i }),
      "regular member must not see the per-row Cancel button",
    ).not.toBeInTheDocument();
  });
});
