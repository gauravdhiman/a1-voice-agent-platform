import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { CreditPurchase } from "../credit-purchase";

const entitlements = (topupEnabled: boolean) => ({
  organization_id: "org-1",
  plan_version_id: "v1",
  plan_product_slug: "pro",
  plan_version_number: 1,
  plan_version_label: "Pro v1",
  is_legacy_version: false,
  is_entitled: true,
  cancel_at_period_end: false,
  access_until: null,
  limits: {},
  features: {
    credit_topup_enabled: {
      key: "credit_topup_enabled",
      kind: "feature",
      assigned: true,
      raw_value: null,
      effective_value: topupEnabled,
      is_unlimited: false,
    },
  },
  migration: null,
});

vi.mock("@/contexts/auth-context", () => ({
  useAuth: () => ({ user: { id: "user-1" } }),
}));

vi.mock("@/hooks/use-credit-products", () => ({
  useCreditProducts: () => ({
    data: [
      {
        id: "prod-1",
        name: "Starter Pack",
        description: "Extra credits",
        credit_amount: 1000,
        price_amount: 1000,
        currency: "$",
      },
    ],
    isLoading: false,
    error: null,
  }),
}));

vi.mock("@/services/billing-service", () => ({
  billingService: {
    getOrganizationEntitlements: vi.fn(),
    createCreditsCheckout: vi.fn(),
  },
}));

vi.mock("@/lib/stripe", () => ({
  getStripe: vi.fn(),
}));

vi.mock("sonner", () => ({
  toast: { error: vi.fn() },
}));

describe("CreditPurchase", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders purchase packages when credit_topup_enabled is on", async () => {
    const { billingService } = await import("@/services/billing-service");
    (billingService.getOrganizationEntitlements as ReturnType<typeof vi.fn>).mockResolvedValue(
      entitlements(true),
    );

    render(<CreditPurchase organizationId="org-1" />);

    expect(await screen.findByText("Starter Pack")).toBeInTheDocument();
    expect(screen.getByText("Purchase Additional Credits")).toBeInTheDocument();
  });

  it("shows an upgrade prompt when credit_topup_enabled is off", async () => {
    const { billingService } = await import("@/services/billing-service");
    (billingService.getOrganizationEntitlements as ReturnType<typeof vi.fn>).mockResolvedValue(
      entitlements(false),
    );

    render(<CreditPurchase organizationId="org-1" />);

    expect(
      await screen.findByText("Credit top-ups not enabled"),
    ).toBeInTheDocument();
    expect(screen.queryByText("Starter Pack")).not.toBeInTheDocument();
  });

  it("defaults to blocked while entitlements are loading", async () => {
    const { billingService } = await import("@/services/billing-service");
    let resolveEntitlements: (value: unknown) => void;
    (billingService.getOrganizationEntitlements as ReturnType<typeof vi.fn>).mockReturnValue(
      new Promise((resolve) => {
        resolveEntitlements = resolve;
      }),
    );

    render(<CreditPurchase organizationId="org-1" />);

    expect(screen.getByText("Loading credit packages...")).toBeInTheDocument();

    resolveEntitlements!(entitlements(false));
    expect(
      await screen.findByText("Credit top-ups not enabled"),
    ).toBeInTheDocument();
  });
});
