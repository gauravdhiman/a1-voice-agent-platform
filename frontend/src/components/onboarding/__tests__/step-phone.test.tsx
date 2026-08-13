import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { StepPhone } from "@/components/onboarding/step-phone";
import type { OnboardingWizardState } from "@/lib/onboarding";
import type { AvailablePhoneNumber } from "@/types/phone-number";

const { searchAvailable, purchaseNumber } = vi.hoisted(() => ({
  searchAvailable: vi.fn(),
  purchaseNumber: vi.fn(),
}));

vi.mock("@/services/phone-number-service", () => ({
  phoneNumberService: { searchAvailable, purchaseNumber },
}));

vi.mock("sonner", () => ({
  toast: { error: vi.fn(), success: vi.fn() },
}));

const AVAILABLE_NUMBER: AvailablePhoneNumber = {
  phone_number: "+14805550100",
  phone_number_type: "local",
  country_code: "US",
  area_code: "480",
  monthly_cost_credits: 200,
  capabilities: { voice: true },
  locality: "Phoenix",
  postal_code: "85001",
};

function baseState(): OnboardingWizardState {
  return {
    businessName: "Smile Dental",
    slug: "smile-dental",
    timezone: "America/Phoenix",
    website: "",
    industry: "dental",
    customIndustry: "",
    location: "123 Main St",
    businessDescription: "",
    agentName: "",
    selectedTemplate: null,
    purchasedPhoneNumber: null,
    createdAgentId: null,
  };
}

describe("StepPhone", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    searchAvailable.mockResolvedValue({
      items: [AVAILABLE_NUMBER],
      total_count: 1,
      page: 1,
      page_size: 5,
      total_pages: 1,
    });
  });

  it("submits the number search when Enter is pressed", async () => {
    const user = userEvent.setup();
    render(
      <StepPhone
        state={baseState()}
        orgId="org-1"
        onChange={vi.fn()}
        onNext={vi.fn()}
        onBack={vi.fn()}
      />,
    );

    await user.type(screen.getByPlaceholderText(/area code/i), "480{Enter}");

    await waitFor(() =>
      expect(searchAvailable).toHaveBeenCalledWith({
        country_code: "US",
        phone_number_type: "local",
        area_code: "480",
        page_size: 5,
      }),
    );
  });
});
