import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { PhoneNumberCancelDialog } from "@/components/phone-numbers/phone-number-cancel-dialog";
import type { PhoneNumberWithAgent } from "@/types/phone-number";

vi.mock("@/services/phone-number-service", () => ({
  phoneNumberService: { cancelNumber: vi.fn() },
}));

const makePhoneNumber = (
  managementMode: "customer_managed" | "platform_managed",
): PhoneNumberWithAgent =>
  ({
    id: "number-1",
    phone_number: "+14805550123",
    management_mode: managementMode,
    is_included_in_plan: false,
    monthly_cost_credits: 80,
    assigned_agent_id: null,
    agent_name: null,
  }) as PhoneNumberWithAgent;

describe("PhoneNumberCancelDialog", () => {
  it("explains that disconnecting a customer-owned number leaves carrier billing with the customer", () => {
    render(
      <PhoneNumberCancelDialog
        organizationId="org-1"
        phoneNumber={makePhoneNumber("customer_managed")}
        open
        onOpenChange={vi.fn()}
        onCancelSuccess={vi.fn()}
      />,
    );

    expect(screen.getByText("Disconnect Phone Number")).toBeTruthy();
    expect(
      screen.getByText(/Twilio ownership and billing remain with you/i),
    ).toBeTruthy();
    expect(screen.getByText("Customer-owned Twilio number")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Disconnect Number" })).toBeTruthy();
  });

  it("explains platform-number release and shows its credit rental rate", async () => {
    const { getByRole, getByPlaceholderText, getByText } = render(
      <PhoneNumberCancelDialog
        organizationId="org-1"
        phoneNumber={makePhoneNumber("platform_managed")}
        open
        onOpenChange={vi.fn()}
        onCancelSuccess={vi.fn()}
      />,
    );

    expect(getByText("Release Phone Number")).toBeTruthy();
    expect(
      getByText(/current billing period is not refunded/i),
    ).toBeTruthy();
    expect(getByText("80 credits/month ($2.00 equivalent)")).toBeTruthy();
    expect((getByRole("button", { name: "Release Number" }) as HTMLButtonElement).disabled).toBe(true);

    fireEvent.change(getByPlaceholderText("Release"), {
      target: { value: "Release" },
    });
    expect((getByRole("button", { name: "Release Number" }) as HTMLButtonElement).disabled).toBe(false);
  });
});
