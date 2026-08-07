import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { StepTemplate } from "@/components/onboarding/step-template";
import type { OnboardingWizardState } from "@/lib/onboarding";
import type { VoiceTemplate } from "@/types/voice-template";

vi.mock("@/services/voice-template-service", () => ({
  voiceTemplateService: {
    listTemplates: vi.fn(),
  },
}));

import { voiceTemplateService } from "@/services/voice-template-service";

const template = {
  id: "tmpl-1",
  name: "Dental Receptionist",
  industry: "dental",
  description: "Friendly dental receptionist",
  greeting: "Thank you for calling [Business Name]! This is Alex.",
  persona: "You are named Alex.",
  tone: "warm",
  mission: "Help patients",
  custom_instructions: null,
} as VoiceTemplate;

function baseState(
  overrides: Partial<OnboardingWizardState> = {},
): OnboardingWizardState {
  return {
    businessName: "Smile Dental",
    slug: "smile-dental",
    timezone: "America/Chicago",
    website: "",
    industry: "dental",
    customIndustry: "",
    location: "123 Main St",
    businessDescription: "",
    agentName: "",
    selectedTemplate: null,
    purchasedPhoneNumber: null,
    createdAgentId: null,
    ...overrides,
  };
}

describe("StepTemplate", () => {
  beforeEach(() => {
    vi.mocked(voiceTemplateService.listTemplates).mockResolvedValue([template]);
  });

  it("disables Continue and Skip until an agent name is entered", async () => {
    render(
      <StepTemplate
        state={baseState()}
        onChange={vi.fn()}
        onNext={vi.fn()}
        onSkip={vi.fn()}
        onBack={vi.fn()}
      />,
    );

    await waitFor(() =>
      expect(screen.getByText("Dental Receptionist")).toBeInTheDocument(),
    );

    expect(screen.getByTestId("onboarding-template-continue")).toBeDisabled();
    expect(screen.getByTestId("onboarding-template-skip")).toBeDisabled();
  });

  it("allows skipping templates when agent name is set", async () => {
    const onSkip = vi.fn();
    render(
      <StepTemplate
        state={baseState({ agentName: "Riley" })}
        onChange={vi.fn()}
        onNext={vi.fn()}
        onSkip={onSkip}
        onBack={vi.fn()}
      />,
    );

    await waitFor(() =>
      expect(screen.getByTestId("onboarding-template-skip")).not.toBeDisabled(),
    );

    expect(screen.getByTestId("onboarding-template-continue")).toBeDisabled();
    fireEvent.click(screen.getByTestId("onboarding-template-skip"));
    expect(onSkip).toHaveBeenCalledTimes(1);
  });

  it("enables Continue when agent name and template are set", async () => {
    const onNext = vi.fn();
    render(
      <StepTemplate
        state={baseState({
          agentName: "Riley",
          selectedTemplate: template,
        })}
        onChange={vi.fn()}
        onNext={onNext}
        onSkip={vi.fn()}
        onBack={vi.fn()}
      />,
    );

    await waitFor(() =>
      expect(
        screen.getByTestId("onboarding-template-continue"),
      ).not.toBeDisabled(),
    );

    fireEvent.click(screen.getByTestId("onboarding-template-continue"));
    expect(onNext).toHaveBeenCalledTimes(1);
  });
});
