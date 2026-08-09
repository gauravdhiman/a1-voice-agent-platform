import * as React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeAll, describe, expect, it, vi } from "vitest";
import { PlatformPlansManager } from "../platform-plans-manager";

const { version, detail } = vi.hoisted(() => {
  const version = {
    id: "version-1",
    plan_product_id: "product-1",
    version_number: 1,
    status: "draft" as const,
    display_label: "Free trial",
    billing_mode: "free" as const,
    credit_grant_policy: "recurring" as const,
    price_amount_cents: 0,
    currency: "USD",
    billing_interval: "monthly",
    trial_period_days: null,
    stripe_product_id: null,
    stripe_price_id: null,
    is_current_for_signup: false,
    published_at: null,
    legacy_subscription_plan_id: null,
    created_at: "2026-08-08T00:00:00Z",
    updated_at: "2026-08-08T00:00:00Z",
  } as const;

  return { version, detail: { ...version, entitlements: [] } };
});

vi.mock("@/services/admin-plan-service", () => ({
  adminPlanService: {
    listPlanProducts: vi.fn().mockResolvedValue([
      {
        id: "product-1",
        slug: "free",
        display_name: "Free",
        description: null,
        sort_order: 1,
        is_active: true,
        stripe_product_id: null,
        created_at: "2026-08-08T00:00:00Z",
        updated_at: "2026-08-08T00:00:00Z",
        versions: [version],
      },
    ]),
    listEntitlementDefinitions: vi.fn().mockResolvedValue([]),
    getPlanVersion: vi.fn().mockResolvedValue(detail),
    updateDraftVersion: vi.fn().mockResolvedValue(detail),
    createDraftVersion: vi.fn(),
    deleteDraftVersion: vi.fn(),
    clonePlanVersion: vi.fn(),
  },
}));

vi.mock("@/components/billing/plan-products-list-panel", () => ({
  PlanProductsListPanel: ({
    onSelectVersion,
  }: {
    onSelectVersion: (v: typeof version) => void;
  }) => (
    <button type="button" onClick={() => onSelectVersion(version)}>
      Select version
    </button>
  ),
}));

vi.mock("@/components/billing/plan-product-create-sheet", () => ({
  PlanProductCreateSheet: () => null,
}));

vi.mock("@/components/billing/plan-publish-dialog", () => ({
  PlanPublishDialog: () => null,
}));

vi.mock("@/components/billing/stripe-sync-alert", () => ({
  StripeSyncAlert: () => null,
}));

vi.mock("@/components/billing/plan-version-entitlement-display", () => ({
  PlanVersionEntitlementDisplay: () => null,
}));

vi.mock("@/components/billing/plan-version-entitlement-editor", () => ({
  PlanVersionEntitlementEditor: () => null,
}));

vi.mock("@/lib/billing/plan-version-entitlements", () => ({
  buildEntitlementInputs: vi.fn().mockReturnValue([]),
  parseAssignedEntitlements: vi.fn().mockReturnValue([]),
}));

describe("PlatformPlansManager", () => {
  beforeAll(() => {
    Object.assign(HTMLElement.prototype, {
      hasPointerCapture: () => false,
      setPointerCapture: () => undefined,
      releasePointerCapture: () => undefined,
      scrollIntoView: () => undefined,
    });
    globalThis.ResizeObserver = class {
      observe() {}
      unobserve() {}
      disconnect() {}
    };
  });

  it("persists the selected credit cadence for a draft plan", async () => {
    const user = userEvent.setup();
    const { adminPlanService } = await import("@/services/admin-plan-service");

    render(<PlatformPlansManager />);
    await user.click(
      await screen.findByRole("button", { name: "Select version" }),
    );

    const cadence = await screen.findByRole("combobox", {
      name: "Included credit cadence",
    });
    await user.click(cadence);
    await user.click(await screen.findByText("One-time activation grant"));
    await user.click(screen.getByRole("button", { name: "Save draft" }));

    expect(adminPlanService.updateDraftVersion).toHaveBeenCalledWith(
      version.id,
      expect.objectContaining({
        billing_mode: "free",
        credit_grant_policy: "one_time",
      }),
    );
  });
});
