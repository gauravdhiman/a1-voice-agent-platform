import React, { StrictMode } from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  StepTest,
  resetOnboardingAgentCreationForTests,
} from "@/components/onboarding/step-test";
import type { OnboardingWizardState } from "@/lib/onboarding";
import type { VoiceTemplate } from "@/types/voice-template";

vi.mock("@/services/agent-service", () => ({
  agentService: {
    createAgent: vi.fn(),
  },
}));

vi.mock("@/services/organization-service", () => ({
  organizationService: {
    completeOnboarding: vi.fn(),
  },
}));

vi.mock("@/components/agents/test-call-modal", () => ({
  TestCallModal: () => null,
}));

vi.mock("sonner", () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}));

import { agentService } from "@/services/agent-service";
import { organizationService } from "@/services/organization-service";
import { toast } from "sonner";

const template = {
  id: "tmpl-1",
  name: "Dental Receptionist",
  industry: "dental",
  greeting: "Thank you for calling [Business Name]! This is Alex.",
  persona: "You are a receptionist named Alex.",
  tone: "warm",
  mission: "Help patients",
  custom_instructions: "Confirm appointments.",
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
    businessDescription: "Family dental",
    agentName: "Riley",
    selectedTemplate: template,
    purchasedPhoneNumber: null,
    createdAgentId: null,
    ...overrides,
  };
}

describe("StepTest", () => {
  beforeEach(() => {
    resetOnboardingAgentCreationForTests();
    vi.mocked(agentService.createAgent).mockReset();
    vi.mocked(organizationService.completeOnboarding).mockReset();
    vi.mocked(toast.error).mockReset();
    vi.mocked(agentService.createAgent).mockResolvedValue({
      id: "agent-1",
      name: "Riley",
    } as never);
    vi.mocked(organizationService.completeOnboarding).mockResolvedValue(
      {} as never,
    );
  });

  it("creates only one agent under React Strict Mode remounts", async () => {
    render(
      <StrictMode>
        <StepTest
          state={baseState()}
          orgId="org-strict"
          onChange={vi.fn()}
          onOnboardingCompleted={vi.fn()}
          onComplete={vi.fn()}
        />
      </StrictMode>,
    );

    await waitFor(() =>
      expect(agentService.createAgent).toHaveBeenCalledTimes(1),
    );
    await waitFor(() =>
      expect(organizationService.completeOnboarding).toHaveBeenCalledTimes(1),
    );
    expect(toast.error).not.toHaveBeenCalled();
  });

  it("does not create a second agent if completeOnboarding fails", async () => {
    vi.mocked(organizationService.completeOnboarding).mockRejectedValue(
      new Error("save failed"),
    );

    render(
      <StrictMode>
        <StepTest
          state={baseState()}
          orgId="org-complete-fail"
          onChange={vi.fn()}
          onOnboardingCompleted={vi.fn()}
          onComplete={vi.fn()}
        />
      </StrictMode>,
    );

    await waitFor(() =>
      expect(agentService.createAgent).toHaveBeenCalledTimes(1),
    );
    await waitFor(() =>
      expect(toast.error).toHaveBeenCalledWith(
        "Agent created, but we couldn't save onboarding status yet.",
      ),
    );
    expect(agentService.createAgent).toHaveBeenCalledTimes(1);
  });

  it("creates the agent with the chosen name and marks onboarding complete", async () => {
    const onOnboardingCompleted = vi.fn();
    const onChange = vi.fn();

    render(
      <StepTest
        state={baseState()}
        orgId="org-1"
        onChange={onChange}
        onOnboardingCompleted={onOnboardingCompleted}
        onComplete={vi.fn()}
      />,
    );

    await waitFor(() =>
      expect(agentService.createAgent).toHaveBeenCalledTimes(1),
    );

    const payload = vi.mocked(agentService.createAgent).mock.calls[0][0];
    expect(payload.name).toBe("Riley");
    expect(payload.persona).toContain("named Riley");
    expect(payload.instructions_markdown).toContain("This is Riley");
    expect(payload.instructions_markdown).not.toContain("This is Alex");

    await waitFor(() =>
      expect(organizationService.completeOnboarding).toHaveBeenCalledWith(
        "org-1",
      ),
    );
    expect(onOnboardingCompleted).toHaveBeenCalled();
    expect(onChange).toHaveBeenCalledWith({ createdAgentId: "agent-1" });
  });

  it("does not show a Back button on the final step", async () => {
    render(
      <StepTest
        state={baseState({ createdAgentId: "agent-1" })}
        orgId="org-1"
        onChange={vi.fn()}
        onOnboardingCompleted={vi.fn()}
        onComplete={vi.fn()}
      />,
    );

    await waitFor(() =>
      expect(screen.getByTestId("onboarding-go-dashboard")).toBeInTheDocument(),
    );
    expect(screen.queryByRole("button", { name: /Back/i })).toBeNull();
  });
});
