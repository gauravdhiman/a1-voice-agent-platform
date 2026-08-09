import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { OnboardingWizardState } from "@/lib/onboarding";

const {
  mockReplace,
  mockUseOrganization,
  mockUseSearchParams,
  mockUpdateOrganization,
  mockCompleteOnboarding,
  mockRefreshOrganizations,
  mockSetCurrentOrganization,
  mockGetSubscriptionActivationStatus,
  mockCreateAgent,
  router,
} = vi.hoisted(() => {
  const mockReplace = vi.fn();
  return {
    mockReplace,
    mockUseOrganization: vi.fn(),
    mockUseSearchParams: vi.fn(),
    mockUpdateOrganization: vi.fn(),
    mockCompleteOnboarding: vi.fn(),
    mockRefreshOrganizations: vi.fn(),
    mockSetCurrentOrganization: vi.fn(),
    mockGetSubscriptionActivationStatus: vi.fn(),
    mockCreateAgent: vi.fn(),
    router: { replace: mockReplace, push: vi.fn(), back: vi.fn() },
  };
});

vi.mock("next/navigation", () => ({
  useRouter: () => router,
  useSearchParams: () => mockUseSearchParams(),
}));

vi.mock("@/contexts/organization-context", () => ({
  useOrganization: () => mockUseOrganization(),
}));

vi.mock("@/services/organization-service", () => ({
  organizationService: {
    updateOrganization: mockUpdateOrganization,
    completeOnboarding: mockCompleteOnboarding,
  },
}));

vi.mock("@/services/billing-service", () => ({
  billingService: {
    getSubscriptionActivationStatus: mockGetSubscriptionActivationStatus,
  },
}));

vi.mock("@/services/agent-service", () => ({
  agentService: { createAgent: mockCreateAgent },
}));

vi.mock("@/components/onboarding/step-org-details", () => ({
  StepOrgDetails: ({
    onChange,
    onNext,
  }: {
    state: OnboardingWizardState;
    onChange: (update: Partial<OnboardingWizardState>) => void;
    onNext: () => void;
    saving: boolean;
  }) => (
    <div data-testid="mock-org-details">
      <button
        onClick={() =>
          onChange({
            businessName: "Acme Updated",
            slug: "acme-updated",
            timezone: "America/Phoenix",
            website: "https://acme.example",
            industry: "hvac",
            customIndustry: "",
            location: "123 Main St, Phoenix, AZ",
            businessDescription: "Heating and cooling services",
          })
        }
      >
        Fill organization details
      </button>
      <button onClick={onNext}>Continue organization setup</button>
    </div>
  ),
}));

vi.mock("@/components/onboarding/step-plan-selection", () => ({
  StepPlanSelection: ({
    onActivated,
    paymentState,
  }: {
    organizationId: string;
    onActivated: (planVersionId: string) => void;
    onBack?: () => void;
    paymentState?: "cancelled" | "failed" | null;
  }) => (
    <div data-testid="mock-plan-selection">
      <span>{paymentState ?? "ready"}</span>
      <button onClick={() => onActivated("free-version")}>
        Activate free plan
      </button>
    </div>
  ),
}));

import OnboardingPage from "./page";

const organization = {
  id: "org-1",
  name: "Acme",
  description: null,
  slug: "acme",
  website: null,
  timezone: null,
  industry: null,
  location: null,
  business_details: null,
  is_active: true,
  onboarding_completed: false,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

describe("founder onboarding page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseSearchParams.mockReturnValue(new URLSearchParams());
    mockUseOrganization.mockReturnValue({
      currentOrganization: organization,
      setCurrentOrganization: mockSetCurrentOrganization,
      refreshOrganizations: mockRefreshOrganizations,
    });
    mockUpdateOrganization.mockResolvedValue(organization);
    mockCompleteOnboarding.mockResolvedValue({
      ...organization,
      onboarding_completed: true,
    });
    mockRefreshOrganizations.mockResolvedValue(undefined);
    mockGetSubscriptionActivationStatus.mockResolvedValue({
      organization_id: organization.id,
      state: "unselected",
      subscription_id: null,
      plan_version_id: null,
      billing_mode: null,
      subscription_status: null,
    });
  });

  it("moves from organization details to plan selection without creating an agent", async () => {
    render(<OnboardingPage />);

    expect(screen.getByTestId("mock-org-details")).toBeInTheDocument();
    expect(screen.queryByTestId("mock-plan-selection")).not.toBeInTheDocument();
    expect(screen.queryByText(/% complete · Step/i)).not.toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("button", { name: /continue organization/i }),
    );

    expect(
      await screen.findByTestId("mock-plan-selection"),
    ).toBeInTheDocument();
    expect(mockCreateAgent).not.toHaveBeenCalled();
  });

  it("submits the selected timezone when saving organization details", async () => {
    render(<OnboardingPage />);

    fireEvent.click(
      screen.getByRole("button", { name: /fill organization details/i }),
    );
    fireEvent.click(
      screen.getByRole("button", { name: /continue organization/i }),
    );

    await waitFor(() => {
      expect(mockUpdateOrganization).toHaveBeenCalledWith("org-1", {
        name: "Acme Updated",
        slug: "acme-updated",
        timezone: "America/Phoenix",
        website: "https://acme.example",
        industry: "hvac",
        location: "123 Main St, Phoenix, AZ",
        business_details: "Heating and cooling services",
      });
    });
  });

  it("resumes directly at plan selection when organization details are saved", async () => {
    mockUseOrganization.mockReturnValue({
      currentOrganization: {
        ...organization,
        timezone: "America/Phoenix",
        industry: "hvac",
        location: "123 Main St, Phoenix, AZ",
      },
      setCurrentOrganization: mockSetCurrentOrganization,
      refreshOrganizations: mockRefreshOrganizations,
    });

    render(<OnboardingPage />);

    expect(
      await screen.findByTestId("mock-plan-selection"),
    ).toBeInTheDocument();
    expect(screen.queryByTestId("mock-org-details")).not.toBeInTheDocument();
  });

  it("completes onboarding after free activation and goes to the dashboard", async () => {
    render(<OnboardingPage />);
    fireEvent.click(
      screen.getByRole("button", { name: /continue organization/i }),
    );
    fireEvent.click(
      await screen.findByRole("button", { name: /activate free/i }),
    );

    await waitFor(() => {
      expect(mockCompleteOnboarding).toHaveBeenCalledWith("org-1");
      expect(mockReplace).toHaveBeenCalledWith("/dashboard");
    });
    expect(mockCreateAgent).not.toHaveBeenCalled();
  });

  it("confirms a paid checkout return before completing onboarding", async () => {
    mockUseSearchParams.mockReturnValue(
      new URLSearchParams("payment=success&organization_id=org-1"),
    );
    mockGetSubscriptionActivationStatus.mockResolvedValue({
      organization_id: organization.id,
      state: "active",
      subscription_id: "subscription-1",
      plan_version_id: "paid-version",
      billing_mode: "paid",
      subscription_status: "active",
    });

    render(<OnboardingPage />);

    expect(
      await screen.findByTestId("mock-plan-selection"),
    ).toBeInTheDocument();
    await waitFor(() => {
      expect(mockGetSubscriptionActivationStatus).toHaveBeenCalledWith("org-1");
      expect(mockCompleteOnboarding).toHaveBeenCalledWith("org-1");
      expect(mockReplace).toHaveBeenCalledWith("/dashboard");
    });
  });

  it("keeps the plan step visible after checkout cancellation", async () => {
    mockUseSearchParams.mockReturnValue(
      new URLSearchParams("payment=cancelled&organization_id=org-1"),
    );

    render(<OnboardingPage />);

    expect(await screen.findByTestId("mock-plan-selection")).toHaveTextContent(
      "cancelled",
    );
    expect(mockCompleteOnboarding).not.toHaveBeenCalled();
  });
});
