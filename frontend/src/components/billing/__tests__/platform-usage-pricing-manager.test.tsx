import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { toast } from "sonner";
import { PlatformUsagePricingManager } from "../platform-usage-pricing-manager";

const events = [
  {
    id: "event-1",
    name: "voice_call_minute",
    description: "One connected voice-call minute",
    credit_cost: 10,
    category: "voice",
    is_active: true,
    metadata: null,
    meter_type: "duration" as const,
    billing_unit: "minute" as const,
    created_at: "2026-08-11T00:00:00Z",
    updated_at: "2026-08-11T00:00:00Z",
  },
  {
    id: "event-2",
    name: "phone_number_local_month",
    description:
      "Existing non-US local platform rentals retain their legacy monthly rate.",
    credit_cost: 200,
    category: "phone_number",
    is_active: true,
    metadata: null,
    meter_type: "count" as const,
    billing_unit: "month" as const,
    created_at: "2026-08-11T00:00:00Z",
    updated_at: "2026-08-11T00:00:00Z",
  },
  {
    id: "event-5",
    name: "phone_number_us_local_month",
    description:
      "Each additional platform-provided US local phone number uses 80 credits per rental month.",
    credit_cost: 80,
    category: "phone_number",
    is_active: true,
    metadata: null,
    meter_type: "count" as const,
    billing_unit: "month" as const,
    created_at: "2026-08-11T00:00:00Z",
    updated_at: "2026-08-11T00:00:00Z",
  },
  {
    id: "event-3",
    name: "phone_number_mobile_month",
    description:
      "Legacy active mobile rentals retain their monthly rate; new mobile-number purchases are unavailable in v1.",
    credit_cost: 200,
    category: "phone_number",
    is_active: true,
    metadata: null,
    meter_type: "count" as const,
    billing_unit: "month" as const,
    created_at: "2026-08-11T00:00:00Z",
    updated_at: "2026-08-11T00:00:00Z",
  },
  {
    id: "event-4",
    name: "phone_number_toll_free_month",
    description:
      "A platform-provided toll-free number uses 120 credits per rental month.",
    credit_cost: 120,
    category: "phone_number",
    is_active: true,
    metadata: null,
    meter_type: "count" as const,
    billing_unit: "month" as const,
    created_at: "2026-08-11T00:00:00Z",
    updated_at: "2026-08-11T00:00:00Z",
  },
];

const { listCreditEvents, updateCreditEvent, useCreditProducts } = vi.hoisted(
  () => ({
    listCreditEvents: vi.fn(),
    updateCreditEvent: vi.fn(),
    useCreditProducts: vi.fn(),
  }),
);

vi.mock("@/services/admin-plan-service", () => ({
  adminPlanService: { listCreditEvents, updateCreditEvent },
}));

vi.mock("@/hooks/use-credit-products", () => ({
  useCreditProducts,
}));

describe("PlatformUsagePricingManager", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    listCreditEvents.mockResolvedValue(events);
    updateCreditEvent.mockResolvedValue({ ...events[0], credit_cost: 0 });
    useCreditProducts.mockReturnValue({
      data: [
        {
          credit_amount: 200,
          price_amount: 500,
          currency: "USD",
          is_active: true,
        },
        {
          credit_amount: 2000,
          price_amount: 4400,
          currency: "USD",
          is_active: true,
        },
      ],
    });
  });
  it("lets an admin set a zero-cost activity and save it", async () => {
    const user = userEvent.setup();
    render(<PlatformUsagePricingManager />);

    const costInput = await screen.findByRole("spinbutton", {
      name: "Credit cost for Voice calls",
    });
    await user.clear(costInput);
    await user.type(costInput, "0");
    await user.click(screen.getAllByRole("button", { name: "Save" })[0]);

    expect(updateCreditEvent).toHaveBeenCalledWith(
      "voice_call_minute",
      expect.objectContaining({ credit_cost: 0 }),
    );
  });

  it("presents all system rates in one comparable table", async () => {
    render(<PlatformUsagePricingManager />);

    expect(
      await screen.findByRole("table", { name: "System usage pricing" }),
    ).toBeTruthy();
    expect(screen.getAllByRole("row")).toHaveLength(6);
    expect(screen.getByText("Voice")).toBeTruthy();
    expect(screen.getAllByText("Phone number")).toHaveLength(4);
    expect(screen.getByText("Voice calls")).toBeTruthy();
    expect(
      screen.getByText("≈ $0.22–$0.25 depending on pack per connected minute"),
    ).toBeTruthy();
    expect(screen.getByText("Additional US local numbers")).toBeTruthy();
    expect(screen.getByText("Legacy non-US local numbers")).toBeTruthy();
    expect(
      screen.getByText("Existing mobile number rentals (legacy)"),
    ).toBeTruthy();
    expect(screen.getByText("Toll-free phone numbers")).toBeTruthy();
    const expectedRates = [
      ["Voice calls", "10"],
      ["Legacy non-US local numbers", "200"],
      ["Additional US local numbers", "80"],
      ["Existing mobile number rentals (legacy)", "200"],
      ["Toll-free phone numbers", "120"],
    ] as const;
    for (const [activity, value] of expectedRates) {
      const input = screen.getByRole("spinbutton", {
        name: `Credit cost for ${activity}`,
      }) as HTMLInputElement;
      expect(input.value).toBe(value);
    }
    expect(screen.getAllByText(/Per active number \/ month/)).toHaveLength(1);
    expect(screen.getByText("Per existing number / month")).toBeTruthy();
    expect(screen.getByText("Per additional number / month")).toBeTruthy();
    expect(screen.queryByRole("combobox")).toBeNull();
    expect(screen.queryByText("Call recording storage")).toBeNull();
  });

  it("explains each activity through a keyboard-accessible tooltip", async () => {
    render(<PlatformUsagePricingManager />);

    const infoButtons = await screen.findAllByRole("button", {
      name: /More information about/,
    });

    expect(infoButtons).toHaveLength(5);
    expect(infoButtons[0].getAttribute("aria-label")).toBe(
      "More information about Voice calls",
    );
    expect(infoButtons[2].getAttribute("aria-label")).toBe(
      "More information about Additional US local numbers",
    );
  });

  it("shows a loading state and an honest empty state", async () => {
    let resolve!: (rows: typeof events) => void;
    listCreditEvents.mockReturnValueOnce(
      new Promise((done) => {
        resolve = done;
      }),
    );
    render(<PlatformUsagePricingManager />);
    expect(screen.getByText("Loading usage pricing…")).toBeTruthy();
    await act(async () => resolve([]));
    expect(
      await screen.findByText("No system usage prices are configured yet."),
    ).toBeTruthy();
  });

  it("distinguishes a failed load from an empty catalog and lets the admin retry", async () => {
    const user = userEvent.setup();
    listCreditEvents.mockRejectedValueOnce(new Error("offline"));
    render(<PlatformUsagePricingManager />);
    expect(await screen.findByRole("alert")).toHaveProperty(
      "textContent",
      expect.stringContaining("Unable to load usage pricing"),
    );
    expect(
      screen.queryByText("No system usage prices are configured yet."),
    ).toBeNull();
    await user.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByRole("table")).toBeTruthy();
  });

  it.each([
    undefined,
    [],
    [
      {
        credit_amount: 200,
        price_amount: 100,
        currency: "EUR",
        is_active: true,
      },
    ],
  ])(
    "does not fabricate USD equivalents when usable USD products are absent (%s)",
    async (data) => {
      useCreditProducts.mockReturnValue({ data });
      render(<PlatformUsagePricingManager />);
      expect(
        await screen.findByText(
          "USD equivalent varies by credit pack per connected minute",
        ),
      ).toBeTruthy();
    },
  );

  it("excludes inactive, invalid and foreign-currency prices from USD equivalents", async () => {
    useCreditProducts.mockReturnValue({
      data: [
        {
          credit_amount: 200,
          price_amount: 500,
          currency: "usd",
          is_active: true,
        },
        {
          credit_amount: 2000,
          price_amount: 4400,
          currency: "USD",
          is_active: true,
        },
        {
          credit_amount: 200,
          price_amount: 100,
          currency: "EUR",
          is_active: true,
        },
        {
          credit_amount: 0,
          price_amount: 500,
          currency: "USD",
          is_active: true,
        },
        {
          credit_amount: 200,
          price_amount: Number.NaN,
          currency: "USD",
          is_active: true,
        },
        {
          credit_amount: 200,
          price_amount: -1,
          currency: "USD",
          is_active: true,
        },
        {
          credit_amount: 200,
          price_amount: 100,
          currency: "USD",
          is_active: false,
        },
      ],
    });
    render(<PlatformUsagePricingManager />);
    expect(
      await screen.findByText(
        "≈ $0.22–$0.25 depending on pack per connected minute",
      ),
    ).toBeTruthy();
  });

  it("uses one equivalent when unit prices are equal and recomputes after editing an activity", async () => {
    const user = userEvent.setup();
    useCreditProducts.mockReturnValue({
      data: [
        {
          credit_amount: 200,
          price_amount: 500,
          currency: "USD",
          is_active: true,
        },
      ],
    });
    render(<PlatformUsagePricingManager />);
    expect(
      await screen.findByText("≈ $0.25 per connected minute"),
    ).toBeTruthy();
    const input = screen.getByRole("spinbutton", {
      name: "Credit cost for Voice calls",
    });
    await user.clear(input);
    await user.type(input, "20");
    expect(screen.getByText("≈ $0.50 per connected minute")).toBeTruthy();
  });

  it("renders future system events and default descriptions accessibly", async () => {
    const user = userEvent.setup();
    listCreditEvents.mockResolvedValue([
      { ...events[0], name: "future_system_activity", description: null },
    ]);
    render(<PlatformUsagePricingManager />);
    expect(await screen.findByText("Future System Activity")).toBeTruthy();
    expect(screen.getByText("System")).toBeTruthy();
    expect(screen.getByText("System-defined activity")).toBeTruthy();
    await user.tab();
    expect(document.activeElement?.getAttribute("aria-label")).toBe(
      "More information about Future System Activity",
    );
    expect((await screen.findByRole("tooltip")).textContent).toBe(
      "No description has been provided.",
    );
  });

  it("disables every save while one request is pending and updates the rate confirmed by the server", async () => {
    const user = userEvent.setup();
    let resolve!: (row: (typeof events)[number]) => void;
    updateCreditEvent.mockReturnValueOnce(
      new Promise((done) => {
        resolve = done;
      }),
    );
    render(<PlatformUsagePricingManager />);
    await screen.findByRole("table");
    await user.click(screen.getAllByRole("button", { name: "Save" })[0]);
    for (const button of screen.getAllByRole("button", { name: "Save" }))
      expect((button as HTMLButtonElement).disabled).toBe(true);
    for (const input of screen.getAllByRole("spinbutton"))
      expect((input as HTMLInputElement).disabled).toBe(true);
    await act(async () => resolve({ ...events[0], credit_cost: 15 }));
    expect(
      (
        screen.getByRole("spinbutton", {
          name: "Credit cost for Voice calls",
        }) as HTMLInputElement
      ).value,
    ).toBe("15");
    expect(toast.success).toHaveBeenCalledWith("Voice calls pricing saved");
  });

  it.each([new Error("Rate update denied"), "offline"])(
    "preserves edits and reenables save after update failure (%s)",
    async (error) => {
      const user = userEvent.setup();
      updateCreditEvent.mockRejectedValueOnce(error);
      render(<PlatformUsagePricingManager />);
      const input = await screen.findByRole("spinbutton", {
        name: "Credit cost for Voice calls",
      });
      await user.clear(input);
      await user.type(input, "25");
      await user.click(screen.getAllByRole("button", { name: "Save" })[0]);
      await waitFor(() =>
        expect(toast.error).toHaveBeenCalledWith(
          error instanceof Error
            ? error.message
            : "Failed to save usage pricing",
        ),
      );
      expect((input as HTMLInputElement).value).toBe("25");
      expect(
        (
          screen.getAllByRole("button", {
            name: "Save",
          })[0] as HTMLButtonElement
        ).disabled,
      ).toBe(false);
    },
  );
});
