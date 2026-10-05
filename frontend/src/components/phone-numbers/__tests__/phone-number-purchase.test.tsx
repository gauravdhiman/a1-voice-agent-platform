import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { purchaseNumber } = vi.hoisted(() => ({
  purchaseNumber: vi.fn(),
}));

vi.mock("@/services/phone-number-service", () => ({
  phoneNumberService: { purchaseNumber },
}));

vi.mock("sonner", () => ({
  toast: { error: vi.fn(), success: vi.fn() },
}));

import { PhoneNumberPurchase } from "../phone-number-purchase";
import type { AvailablePhoneNumber } from "@/types/phone-number";

const INCLUDED_NUMBER: AvailablePhoneNumber = {
  phone_number: "+14805550100",
  phone_number_type: "local",
  country_code: "US",
  area_code: "480",
  monthly_cost_credits: 0,
  is_included_in_plan: true,
  capabilities: { voice: true },
  locality: "Phoenix",
  postal_code: "85001",
};

const ADDITIONAL_NUMBER: AvailablePhoneNumber = {
  ...INCLUDED_NUMBER,
  phone_number: "+14805550101",
  monthly_cost_credits: 80,
  is_included_in_plan: false,
};

describe("PhoneNumberPurchase", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    purchaseNumber.mockResolvedValue({
      success: true,
      phone_number: { id: "number-1", phone_number: INCLUDED_NUMBER.phone_number },
      message: "created",
      credit_balance_after: 0,
    });
  });

  it("explains the shared credit cost before purchasing an additional line", async () => {
    const user = userEvent.setup();
    render(
      <PhoneNumberPurchase
        organizationId="org-1"
        creditBalance={200}
        selectedNumber={ADDITIONAL_NUMBER}
        open
        onOpenChange={vi.fn()}
      />,
    );

    expect(screen.getByText(/80 credits per month \(\$2 equivalent\)/i)).toBeTruthy();
    expect(screen.getByText(/first rental month is charged now/i)).toBeTruthy();
    expect(
      (screen.getByRole("button", { name: "Add Number" }) as HTMLButtonElement)
        .disabled,
    ).toBe(true);

    await user.click(
      screen.getByLabelText(/I understand the first rental month costs 80 credits/i),
    );
    await user.click(screen.getByRole("button", { name: "Add Number" }));

    await waitFor(() =>
      expect(purchaseNumber).toHaveBeenCalledWith(
        "org-1",
        expect.objectContaining({
          phone_number: ADDITIONAL_NUMBER.phone_number,
          expected_included_in_plan: false,
        }),
      ),
    );
  });

  it("lets users get the included number without an acknowledgment or balance", async () => {
    const user = userEvent.setup();
    render(
      <PhoneNumberPurchase
        organizationId="org-1"
        creditBalance={0}
        selectedNumber={INCLUDED_NUMBER}
        open
        onOpenChange={vi.fn()}
      />,
    );

    const addButton = screen.getByRole("button", { name: "Add Number" });
    expect((addButton as HTMLButtonElement).disabled).toBe(false);
    expect(
      screen.queryByLabelText(/I understand this number uses/i),
    ).toBeNull();
    await user.click(addButton);

    await waitFor(() =>
      expect(purchaseNumber).toHaveBeenCalledWith(
        "org-1",
        expect.objectContaining({
          phone_number: INCLUDED_NUMBER.phone_number,
          expected_included_in_plan: true,
        }),
      ),
    );
  });
});
