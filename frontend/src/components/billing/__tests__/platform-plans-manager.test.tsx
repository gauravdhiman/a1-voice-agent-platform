import * as React from "react";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeAll, describe, expect, it, vi } from "vitest";
import { PlatformPlansManager } from "../platform-plans-manager";

const { version, detail, publishedVersion, publishedDetail } = vi.hoisted(
  () => {
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

    const publishedVersion = {
      ...version,
      id: "version-2",
      version_number: 2,
      status: "published" as const,
      display_label: "Published free trial",
      published_at: "2026-08-09T00:00:00Z",
    } as const;

    return {
      version,
      detail: { ...version, entitlements: [] },
      publishedVersion,
      publishedDetail: { ...publishedVersion, entitlements: [] },
    };
  },
);

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
        versions: [version, publishedVersion],
      },
    ]),
    listEntitlementDefinitions: vi.fn().mockResolvedValue([]),
    getPlanVersion: vi
      .fn()
      .mockImplementation((versionId: string) =>
        Promise.resolve(
          versionId === publishedVersion.id ? publishedDetail : detail,
        ),
      ),
    updateDraftVersion: vi.fn().mockResolvedValue(detail),
    createDraftVersion: vi.fn(),
    deleteDraftVersion: vi.fn(),
    clonePlanVersion: vi.fn(),
  },
}));

vi.mock("@/components/billing/plan-products-list-panel", () => ({
  PlanProductsListPanel: ({
    onSelectVersion,
    onCreateDraft,
  }: {
    onSelectVersion: (v: typeof version | typeof publishedVersion) => void;
    onCreateDraft: (product: {
      id: string;
      slug: string;
      versions: never[];
    }) => void;
  }) => (
    <>
      <button type="button" onClick={() => onSelectVersion(version)}>
        Select version
      </button>
      <button type="button" onClick={() => onSelectVersion(publishedVersion)}>
        Select published version
      </button>
      <button
        type="button"
        onClick={() =>
          onCreateDraft({ id: "product-1", slug: "free", versions: [] })
        }
      >
        Create draft
      </button>
    </>
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
        stripe_product_id: null,
        stripe_price_id: null,
      }),
    );
  });

  it("hides Stripe controls for free drafts", async () => {
    const user = userEvent.setup();

    render(<PlatformPlansManager />);
    await user.click(
      await screen.findByRole("button", { name: "Select version" }),
    );

    expect(screen.queryByText("Stripe product ID")).not.toBeInTheDocument();
    expect(
      screen.queryByText("Stripe Product not linked"),
    ).not.toBeInTheDocument();
  });

  it("brings selected version details into view on narrow layouts", async () => {
    const user = userEvent.setup();
    const scrollIntoView = vi
      .spyOn(HTMLElement.prototype, "scrollIntoView")
      .mockImplementation(() => undefined);
    const originalMatchMedia = window.matchMedia;
    window.matchMedia = vi.fn().mockImplementation((query) => ({
      matches: true,
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }));

    try {
      render(<PlatformPlansManager />);
      await user.click(
        await screen.findByRole("button", { name: "Select published version" }),
      );

      await waitFor(() => {
        expect(scrollIntoView).toHaveBeenCalled();
      });
    } finally {
      window.matchMedia = originalMatchMedia;
      scrollIntoView.mockRestore();
    }
  });

  it("creates the free product draft in free billing mode", async () => {
    const user = userEvent.setup();
    const { adminPlanService } = await import("@/services/admin-plan-service");
    vi.mocked(adminPlanService.createDraftVersion).mockResolvedValue(detail);

    render(<PlatformPlansManager />);
    await user.click(
      await screen.findByRole("button", { name: "Create draft" }),
    );

    expect(adminPlanService.createDraftVersion).toHaveBeenCalledWith(
      "product-1",
      expect.objectContaining({ billing_mode: "free", price_amount_cents: 0 }),
    );
  });

  it("previews a draft card and can return to editing", async () => {
    const user = userEvent.setup();

    render(<PlatformPlansManager />);
    await user.click(
      await screen.findByRole("button", { name: "Select version" }),
    );
    await user.click(screen.getByRole("button", { name: "Preview" }));

    expect(
      await screen.findByTestId("plan-preview-card-version-1"),
    ).toBeInTheDocument();
    const draftCard = screen.getByTestId("plan-preview-card-version-1");
    expect(
      within(draftCard).getByRole("button", { name: "Start with Free" }),
    ).toBeDisabled();
    expect(
      within(draftCard).queryByRole("button", { name: "Back to edit" }),
    ).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Publish" })).toBeInTheDocument();
    const draftBack = screen.getByRole("button", { name: "Back to edit" });
    expect(draftBack).toBeInTheDocument();
    expect(
      draftCard.compareDocumentPosition(draftBack) &
        Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();

    await user.click(screen.getByRole("button", { name: "Back to edit" }));

    expect(
      screen.getByTestId("plan-preview-card-version-1").parentElement,
    ).toHaveAttribute("aria-hidden", "true");
    expect(screen.getByRole("button", { name: "Preview" })).toBeInTheDocument();
  });

  it("previews a published card and can return to version details", async () => {
    const user = userEvent.setup();

    render(<PlatformPlansManager />);
    await user.click(
      await screen.findByRole("button", { name: "Select published version" }),
    );
    await user.click(screen.getByRole("button", { name: "Preview" }));

    expect(
      await screen.findByTestId("plan-preview-card-version-2"),
    ).toBeInTheDocument();
    expect(screen.getByText("Published preview")).toBeInTheDocument();
    const publishedCard = screen.getByTestId("plan-preview-card-version-2");
    expect(
      within(publishedCard).getByRole("button", { name: "Start with Free" }),
    ).toBeDisabled();
    expect(
      within(publishedCard).queryByRole("button", {
        name: "Back to version details",
      }),
    ).not.toBeInTheDocument();

    const publishedBack = screen.getByRole("button", {
      name: "Back to version details",
    });
    expect(
      publishedCard.compareDocumentPosition(publishedBack) &
        Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();

    await user.click(publishedBack);

    expect(
      screen.getByTestId("plan-preview-card-version-2").parentElement,
    ).toHaveAttribute("aria-hidden", "true");
  });
});
