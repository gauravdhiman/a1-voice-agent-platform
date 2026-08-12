import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
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
    description: "An active local phone number is charged once per month.",
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
    id: "event-3",
    name: "phone_number_mobile_month",
    description: "An active mobile phone number is charged once per month.",
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
    description: "An active toll-free phone number is charged once per month.",
    credit_cost: 500,
    category: "phone_number",
    is_active: true,
    metadata: null,
    meter_type: "count" as const,
    billing_unit: "month" as const,
    created_at: "2026-08-11T00:00:00Z",
    updated_at: "2026-08-11T00:00:00Z",
  },
];

const { listCreditEvents, updateCreditEvent } = vi.hoisted(() => ({
  listCreditEvents: vi.fn(),
  updateCreditEvent: vi.fn(),
}));

listCreditEvents.mockResolvedValue(events);
updateCreditEvent.mockResolvedValue({ ...events[0], credit_cost: 0 });

vi.mock("@/services/admin-plan-service", () => ({
  adminPlanService: { listCreditEvents, updateCreditEvent },
}));

describe("PlatformUsagePricingManager", () => {
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
    ).toBeInTheDocument();
    expect(screen.getAllByRole("row")).toHaveLength(5);
    expect(screen.getByText("Voice")).toBeInTheDocument();
    expect(screen.getAllByText("Phone number")).toHaveLength(3);
    expect(screen.getByText("Voice calls")).toBeInTheDocument();
    expect(screen.getByText("Local phone numbers")).toBeInTheDocument();
    expect(screen.getByText("Mobile phone numbers")).toBeInTheDocument();
    expect(screen.getByText("Toll-free phone numbers")).toBeInTheDocument();
    expect(screen.getAllByText("Per active number / month")).toHaveLength(3);
    expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
    expect(screen.queryByText("Call recording storage")).not.toBeInTheDocument();
  });

  it("explains each activity through a keyboard-accessible tooltip", async () => {
    render(<PlatformUsagePricingManager />);

    const infoButtons = await screen.findAllByRole("button", {
      name: /More information about/,
    });

    expect(infoButtons).toHaveLength(4);
    expect(infoButtons[0]).toHaveAccessibleName("More information about Voice calls");
    expect(infoButtons[1]).toHaveAccessibleName(
      "More information about Local phone numbers",
    );
  });
});
