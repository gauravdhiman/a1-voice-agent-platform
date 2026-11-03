import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { StepOrgDetails } from "@/components/onboarding/step-org-details";
import type { OnboardingWizardState } from "@/lib/onboarding";

function baseState(
  overrides: Partial<OnboardingWizardState> = {},
): OnboardingWizardState {
  return {
    businessName: "",
    slug: "",
    timezone: "",
    website: "",
    industry: "",
    customIndustry: "",
    location: "",
    businessDescription: "",
    agentName: "",
    selectedTemplate: null,
    purchasedPhoneNumber: null,
    createdAgentId: null,
    ...overrides,
  };
}

describe("StepOrgDetails", () => {
  it("keeps Continue disabled until required fields are filled", () => {
    const onNext = vi.fn();
    render(
      <StepOrgDetails
        organizationId="org-1"
        state={baseState()}
        onChange={vi.fn()}
        onNext={onNext}
        saving={false}
      />,
    );

    expect(screen.getByTestId("onboarding-org-continue")).toBeDisabled();
  });

  it("enables Continue when required organization fields are complete", () => {
    const onNext = vi.fn();
    render(
      <StepOrgDetails
        organizationId="org-1"
        state={baseState({
          businessName: "Acme Plumbing",
          slug: "acme-plumbing",
          timezone: "America/Chicago",
          industry: "plumbing",
          location: "123 Main St, Austin, TX 78701",
        })}
        onChange={vi.fn()}
        onNext={onNext}
        saving={false}
      />,
    );

    const button = screen.getByTestId("onboarding-org-continue");
    expect(button).not.toBeDisabled();
    fireEvent.click(button);
    expect(onNext).toHaveBeenCalledTimes(1);
  });

  it("shows a custom industry field when Other is selected", () => {
    render(
      <StepOrgDetails
        organizationId="org-1"
        state={baseState({
          businessName: "Acme",
          slug: "acme",
          timezone: "America/Chicago",
          industry: "other",
          customIndustry: "",
          location: "123 Main St",
        })}
        onChange={vi.fn()}
        onNext={vi.fn()}
        saving={false}
      />,
    );

    expect(screen.getByTestId("onboarding-org-industry-other")).toBeInTheDocument();
    expect(screen.getByTestId("onboarding-org-continue")).toBeDisabled();
  });
});
