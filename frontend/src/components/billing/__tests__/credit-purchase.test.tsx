import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { CreditProduct, OrgEntitlements } from "@/types/billing";
import { CreditPurchase } from "../credit-purchase";

const mocks = vi.hoisted(() => ({
  useAuth: vi.fn(),
  useCreditProducts: vi.fn(),
  getOrganizationEntitlements: vi.fn(),
  getCreditEvents: vi.fn(),
  createCreditsCheckout: vi.fn(),
  getStripe: vi.fn(),
  redirectToCheckout: vi.fn(),
  toastError: vi.fn(),
  refetch: vi.fn(),
}));

vi.mock("@/contexts/auth-context", () => ({ useAuth: mocks.useAuth }));
vi.mock("@/hooks/use-credit-products", () => ({
  useCreditProducts: mocks.useCreditProducts,
}));
vi.mock("@/services/billing-service", () => ({
  billingService: {
    getOrganizationEntitlements: mocks.getOrganizationEntitlements,
    getCreditEvents: mocks.getCreditEvents,
    createCreditsCheckout: mocks.createCreditsCheckout,
  },
}));
vi.mock("@/lib/stripe", () => ({ getStripe: mocks.getStripe }));
vi.mock("sonner", () => ({ toast: { error: mocks.toastError } }));

function entitlements(
  enabled: boolean,
  organizationId = "org-1",
): OrgEntitlements {
  return {
    organization_id: organizationId,
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
        effective_value: enabled,
        is_unlimited: false,
      },
    },
    migration: null,
  };
}

function product(
  credits: number,
  cents: number,
  currency = "USD",
): CreditProduct {
  return {
    id: `prod-${currency}-${credits}`,
    name: `${credits} Credits Pack`,
    description: "Extra credits",
    stripe_price_id: `price-${currency}-${credits}`,
    stripe_product_id: `stripe-${currency}-${credits}`,
    credit_amount: credits,
    price_amount: cents,
    currency,
    is_active: true,
    created_at: "2026-10-07T00:00:00Z",
    updated_at: "2026-10-07T00:00:00Z",
  };
}

const products = [
  product(200, 500),
  product(500, 1200),
  product(1000, 2300),
  product(2000, 4400),
];

function setProducts(
  data: CreditProduct[] | undefined,
  error: Error | null = null,
  isLoading = false,
) {
  mocks.useCreditProducts.mockReturnValue({
    data,
    error,
    isLoading,
    refetch: mocks.refetch,
  });
}

function setVoiceRate(rate: number) {
  mocks.getCreditEvents.mockResolvedValue([
    { name: "voice_call_minute", credit_cost: rate, is_active: true },
  ]);
}

describe("CreditPurchase", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    mocks.useAuth.mockReturnValue({ user: { id: "user-1" } });
    mocks.getOrganizationEntitlements.mockResolvedValue(entitlements(true));
    mocks.createCreditsCheckout.mockResolvedValue({
      session_id: "cs_test_checkout",
    });
    mocks.redirectToCheckout.mockResolvedValue({});
    mocks.getStripe.mockResolvedValue({
      redirectToCheckout: mocks.redirectToCheckout,
    });
    setProducts(products);
    setVoiceRate(10);
  });

  it("shows four packs with actual minutes, progressively cheaper rates and the best-value badge", async () => {
    render(<CreditPurchase organizationId="org-1" />);
    expect(await screen.findByText("200 Credits Pack")).toBeTruthy();
    for (const amount of [20, 50, 100, 200]) {
      expect(screen.getByText(`Up to ${amount} call minutes`)).toBeTruthy();
    }
    for (const rate of ["0.25", "0.24", "0.23", "0.22"]) {
      expect(screen.getByText(`$${rate} per call minute`)).toBeTruthy();
    }
    for (const savings of [4, 8, 12]) {
      expect(
        screen.getByText(`${savings}% lower per-minute rate`),
      ).toBeTruthy();
    }
    expect(
      within(
        screen
          .getByText("2000 Credits Pack")
          .closest<HTMLElement>('[data-slot="card"]')!,
      ).getByText("Best Value"),
    ).toBeTruthy();
    expect(mocks.getCreditEvents).toHaveBeenCalledTimes(1);
  });

  it("reserves the same description height and footer alignment for every pack", async () => {
    render(<CreditPurchase organizationId="org-1" />);
    await screen.findByText("200 Credits Pack");
    for (const pack of products) {
      const card = screen
        .getByText(pack.name)
        .closest<HTMLElement>('[data-slot="card"]')!;
      expect(
        card
          .querySelector('[data-slot="card-description"]')
          ?.classList.contains("min-h-[3rem]"),
      ).toBe(true);
      expect(card.classList.contains("flex-col")).toBe(true);
      expect(
        card
          .querySelector('[data-slot="card-footer"]')
          ?.classList.contains("mt-auto"),
      ).toBe(true);
    }
  });

  it("uses the current activity rate rather than assuming ten credits per minute", async () => {
    setVoiceRate(20);
    render(<CreditPurchase organizationId="org-1" />);
    expect(await screen.findByText("Up to 10 call minutes")).toBeTruthy();
    expect(screen.getByText("$0.50 per call minute")).toBeTruthy();
    expect(
      screen.getByText("• Voice calls use 20 credits per connected minute"),
    ).toBeTruthy();
  });

  it("describes zero-cost calls without dividing by zero or advertising a finite allowance", async () => {
    setVoiceRate(0);
    render(<CreditPurchase organizationId="org-1" />);
    expect(
      await screen.findByText(
        "• Voice calls are currently included without a credit charge",
      ),
    ).toBeTruthy();
    expect(screen.queryByText(/Up to .* call minutes/)).toBeNull();
    expect(screen.queryByText(/per call minute/)).toBeNull();
    expect(screen.getAllByText(/per credit/)).toHaveLength(4);
  });

  it.each(["missing", "failure", "inactive", "negative", "not finite"])(
    "keeps top-ups usable with accurate credits-only details when voice pricing is %s",
    async (scenario) => {
      if (scenario === "failure")
        mocks.getCreditEvents.mockRejectedValue(new Error("unavailable"));
      else if (scenario === "missing")
        mocks.getCreditEvents.mockResolvedValue([]);
      else if (scenario === "inactive")
        mocks.getCreditEvents.mockResolvedValue([
          { name: "voice_call_minute", credit_cost: 10, is_active: false },
        ]);
      else setVoiceRate(scenario === "negative" ? -1 : Number.NaN);
      render(<CreditPurchase organizationId="org-1" />);
      expect(
        await screen.findByRole("button", { name: "Purchase 200" }),
      ).toBeTruthy();
      expect(screen.queryByText(/Up to .* call minutes/)).toBeNull();
      expect(screen.queryByText(/per call minute/)).toBeNull();
      expect(screen.getAllByText(/per credit/)).toHaveLength(4);
    },
  );

  it("orders unsorted packages and compares discounts only within the same currency", async () => {
    setProducts([
      product(2000, 4400),
      product(300, 600, "EUR"),
      product(200, 500),
    ]);
    render(<CreditPurchase organizationId="org-1" />);
    await screen.findByText("300 Credits Pack");
    expect(
      screen
        .getAllByRole("button", { name: /^Purchase / })
        .map((button) => button.textContent),
    ).toEqual(["Purchase 200", "Purchase 300", "Purchase 2,000"]);
    expect(screen.getByText("12% lower per-minute rate")).toBeTruthy();
    const euroCard = screen
      .getByText("300 Credits Pack")
      .closest<HTMLElement>('[data-slot="card"]')!;
    expect(within(euroCard).getByText("€0.20 per call minute")).toBeTruthy();
    expect(within(euroCard).queryByText("Best Value")).toBeNull();
    expect(within(euroCard).getByText("Standard per-minute rate")).toBeTruthy();
  });

  it("does not claim special value for equal-priced packs", async () => {
    setProducts([product(200, 500), product(1000, 2500)]);
    render(<CreditPurchase organizationId="org-1" />);
    await screen.findByText("200 Credits Pack");
    expect(screen.queryByText("Best Value")).toBeNull();
    expect(screen.getAllByText("Standard per-minute rate")).toHaveLength(2);
  });

  it("filters inactive or malformed packs so it cannot advertise invalid arithmetic", async () => {
    setProducts([
      products[0],
      { ...product(1000, 2300), is_active: false },
      product(0, 100),
      product(500, Number.NaN),
      product(600, -1),
      product(700, 1500, "invalid"),
    ]);
    render(<CreditPurchase organizationId="org-1" />);
    await screen.findByText("200 Credits Pack");
    expect(screen.getAllByRole("button", { name: /^Purchase / })).toHaveLength(
      1,
    );
  });

  it("shows a safe upgrade prompt when the feature is absent or disabled", async () => {
    mocks.getOrganizationEntitlements.mockResolvedValue({
      ...entitlements(false),
      features: {},
    });
    render(<CreditPurchase organizationId="org-1" />);
    expect(await screen.findByText("Credit top-ups not enabled")).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Purchase 200" })).toBeNull();
  });

  it("remains blocked until both catalog and entitlement loading finish", async () => {
    setProducts(undefined, null, true);
    render(<CreditPurchase organizationId="org-1" />);
    expect(screen.getByText("Loading credit packages...")).toBeTruthy();
  });

  it("shows an empty state when there are no usable products", async () => {
    setProducts(undefined);
    render(<CreditPurchase organizationId="org-1" />);
    expect(
      await screen.findByText("No credit packages available"),
    ).toBeTruthy();
  });

  it("shows a retriable catalog error without issuing a toast on every render", async () => {
    const user = userEvent.setup();
    setProducts(undefined, new Error("Catalog unavailable"));
    render(<CreditPurchase organizationId="org-1" />);
    expect(await screen.findByRole("alert")).toHaveProperty(
      "textContent",
      expect.stringContaining("Unable to load credit packages"),
    );
    await user.click(screen.getByRole("button", { name: "Try again" }));
    expect(mocks.refetch).toHaveBeenCalledTimes(1);
    expect(mocks.toastError).not.toHaveBeenCalled();
  });

  it("recovers from an entitlement fetch failure rather than loading forever", async () => {
    const user = userEvent.setup();
    mocks.getOrganizationEntitlements.mockRejectedValueOnce(
      new Error("offline"),
    );
    render(<CreditPurchase organizationId="org-1" />);
    expect(await screen.findByRole("alert")).toHaveProperty(
      "textContent",
      expect.stringContaining("Unable to check credit top-up availability"),
    );
    await user.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByText("200 Credits Pack")).toBeTruthy();
  });

  it("clears the previous organization's permission and ignores its delayed response", async () => {
    let resolveOld!: (value: OrgEntitlements) => void;
    mocks.getOrganizationEntitlements.mockReturnValueOnce(
      new Promise((resolve) => {
        resolveOld = resolve;
      }),
    );
    const view = render(<CreditPurchase organizationId="org-old" />);
    mocks.getOrganizationEntitlements.mockResolvedValueOnce(
      entitlements(false, "org-new"),
    );
    view.rerender(<CreditPurchase organizationId="org-new" />);
    expect(screen.queryByRole("button", { name: "Purchase 200" })).toBeNull();
    expect(await screen.findByText("Credit top-ups not enabled")).toBeTruthy();
    await act(async () => resolveOld(entitlements(true, "org-old")));
    expect(screen.getByText("Credit top-ups not enabled")).toBeTruthy();
  });

  it("hides already enabled top-ups immediately while checking the next organization", async () => {
    let resolveNew!: (value: OrgEntitlements) => void;
    const view = render(<CreditPurchase organizationId="org-1" />);
    await screen.findByRole("button", { name: "Purchase 200" });
    mocks.getOrganizationEntitlements.mockReturnValueOnce(
      new Promise((resolve) => {
        resolveNew = resolve;
      }),
    );
    view.rerender(<CreditPurchase organizationId="org-2" />);
    expect(screen.getByText("Loading credit packages...")).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Purchase 200" })).toBeNull();
    await act(async () => resolveNew(entitlements(false, "org-2")));
    expect(screen.getByText("Credit top-ups not enabled")).toBeTruthy();
  });

  it("ignores an earlier organization's entitlement error after switching successfully", async () => {
    let rejectOld!: (error: Error) => void;
    mocks.getOrganizationEntitlements.mockReturnValueOnce(
      new Promise((_resolve, reject) => {
        rejectOld = reject;
      }),
    );
    const view = render(<CreditPurchase organizationId="org-old" />);
    view.rerender(<CreditPurchase organizationId="org-1" />);
    await screen.findByRole("button", { name: "Purchase 200" });
    await act(async () => rejectOld(new Error("Old request failed")));
    expect(screen.queryByRole("alert")).toBeNull();
    expect(screen.getByRole("button", { name: "Purchase 200" })).toBeTruthy();
  });

  it("requires signing in before creating checkout", async () => {
    const user = userEvent.setup();
    mocks.useAuth.mockReturnValue({ user: null });
    render(<CreditPurchase organizationId="org-1" />);
    await user.click(
      await screen.findByRole("button", { name: "Purchase 200" }),
    );
    expect(mocks.createCreditsCheckout).not.toHaveBeenCalled();
    expect(mocks.toastError).toHaveBeenCalledWith(
      "Please sign in to purchase credits",
    );
  });

  it("creates checkout with the selected product and active organization, disabling every pack while pending", async () => {
    const user = userEvent.setup();
    let resolveCheckout!: (value: { session_id: string }) => void;
    mocks.createCreditsCheckout.mockReturnValueOnce(
      new Promise((resolve) => {
        resolveCheckout = resolve;
      }),
    );
    const onCreditsPurchased = vi.fn();
    render(
      <CreditPurchase
        organizationId="org-1"
        onCreditsPurchased={onCreditsPurchased}
      />,
    );
    await user.click(
      await screen.findByRole("button", { name: "Purchase 1,000" }),
    );
    expect(mocks.createCreditsCheckout).toHaveBeenCalledWith(
      products[2].id,
      "org-1",
    );
    for (const button of screen.getAllByRole("button"))
      expect((button as HTMLButtonElement).disabled).toBe(true);
    await act(async () => resolveCheckout({ session_id: "cs_test_checkout" }));
    expect(mocks.redirectToCheckout).toHaveBeenCalledWith({
      sessionId: "cs_test_checkout",
    });
    expect(onCreditsPurchased).toHaveBeenCalledWith(products[2]);
  });

  it.each(["API", "Stripe load", "Stripe redirect"])(
    "allows retry after a %s checkout failure",
    async (scenario) => {
      const user = userEvent.setup();
      if (scenario === "API")
        mocks.createCreditsCheckout.mockRejectedValueOnce(new Error("offline"));
      if (scenario === "Stripe load")
        mocks.getStripe.mockResolvedValueOnce(null);
      if (scenario === "Stripe redirect")
        mocks.redirectToCheckout.mockResolvedValueOnce({
          error: { message: "declined" },
        });
      const onCreditsPurchased = vi.fn();
      render(
        <CreditPurchase
          organizationId="org-1"
          onCreditsPurchased={onCreditsPurchased}
        />,
      );
      await user.click(
        await screen.findByRole("button", { name: "Purchase 200" }),
      );
      await waitFor(() =>
        expect(mocks.toastError).toHaveBeenCalledWith(
          "Failed to start checkout process",
        ),
      );
      expect(onCreditsPurchased).not.toHaveBeenCalled();
      expect(
        (
          screen.getByRole("button", {
            name: "Purchase 200",
          }) as HTMLButtonElement
        ).disabled,
      ).toBe(false);
      await user.click(screen.getByRole("button", { name: "Purchase 200" }));
      expect(mocks.createCreditsCheckout).toHaveBeenCalledTimes(2);
    },
  );

  it("scrolls to and focuses the purchase section when requested", async () => {
    const scroll = vi.fn();
    Element.prototype.scrollIntoView = scroll;
    render(<CreditPurchase organizationId="org-1" autoFocusPurchase />);
    const section = await screen.findByTestId("credit-purchase-section");
    await waitFor(() =>
      expect(scroll).toHaveBeenCalledWith({
        behavior: "smooth",
        block: "start",
      }),
    );
    expect(document.activeElement).toBe(section);
  });
});
