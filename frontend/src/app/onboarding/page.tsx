"use client";

/**
 * Founder onboarding page.
 *
 * Collects organization details first, then requires an active free or paid
 * subscription before the founder can enter the dashboard. Agent creation is
 * intentionally deferred to the dashboard so every new workspace starts with
 * a usable entitlement.
 */

import React, { useCallback, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Loader2, Phone } from "lucide-react";
import { toast } from "sonner";
import { StepOrgDetails } from "@/components/onboarding/step-org-details";
import { StepPlanSelection } from "@/components/onboarding/step-plan-selection";
import { useOrganization } from "@/contexts/organization-context";
import {
  isOrgDetailsStepComplete,
  parseIndustrySelection,
  resolveIndustryValue,
  suggestAgentName,
  type OnboardingWizardState,
} from "@/lib/onboarding";
import { suggestOrganizationSlugFromName } from "@/lib/organization-slug";
import { billingService } from "@/services/billing-service";
import { organizationService } from "@/services/organization-service";
import type { Organization } from "@/types/organization";

const PAYMENT_POLL_LIMIT = 15;
const PAYMENT_POLL_INTERVAL_MS = 2000;

/**
 * Determine whether an organization has enough persisted profile data to skip
 * the details stage when the founder returns to onboarding.
 *
 * @param organization - Organization returned by the API or organization context
 * @returns True when all required details are already saved
 */
function hasSavedOrganizationDetails(organization: Organization): boolean {
  const industry = parseIndustrySelection(organization.industry);
  return isOrgDetailsStepComplete({
    businessName: organization.name,
    slug: organization.slug,
    timezone: organization.timezone ?? "",
    industry: industry.selection,
    customIndustry: industry.custom,
    location: organization.location ?? "",
  });
}

export default function OnboardingPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { currentOrganization, setCurrentOrganization, refreshOrganizations } =
    useOrganization();
  const [step, setStep] = useState(() =>
    currentOrganization && hasSavedOrganizationDetails(currentOrganization)
      ? 2
      : 1,
  );
  const [saving, setSaving] = useState(false);
  const [paymentState, setPaymentState] = useState<"failed" | null>(null);
  const completionInFlight = useRef(false);

  const industryParsed = parseIndustrySelection(
    currentOrganization?.industry ?? "",
  );

  const [wizardState, setWizardState] = useState<OnboardingWizardState>(() => ({
    businessName: currentOrganization?.name ?? "",
    slug:
      currentOrganization?.slug ??
      suggestOrganizationSlugFromName(currentOrganization?.name ?? ""),
    timezone: currentOrganization?.timezone ?? "",
    website: currentOrganization?.website ?? "",
    industry: industryParsed.selection,
    customIndustry: industryParsed.custom,
    location: currentOrganization?.location ?? "",
    businessDescription: currentOrganization?.business_details ?? "",
    agentName: suggestAgentName(currentOrganization?.name ?? ""),
    selectedTemplate: null,
    purchasedPhoneNumber: null,
    createdAgentId: null,
  }));

  useEffect(() => {
    if (currentOrganization?.onboarding_completed) {
      router.replace("/dashboard");
    }
  }, [currentOrganization?.onboarding_completed, router]);

  useEffect(() => {
    if (!currentOrganization) return;
    const parsed = parseIndustrySelection(currentOrganization.industry);
    setWizardState((state) => ({
      ...state,
      businessName: state.businessName || currentOrganization.name,
      slug: state.slug || currentOrganization.slug,
      timezone: state.timezone || currentOrganization.timezone || "",
      website: state.website || currentOrganization.website || "",
      industry: state.industry || parsed.selection,
      customIndustry: state.customIndustry || parsed.custom,
      location: state.location || currentOrganization.location || "",
      businessDescription:
        state.businessDescription || currentOrganization.business_details || "",
      agentName: state.agentName || suggestAgentName(currentOrganization.name),
    }));
  }, [currentOrganization]);

  useEffect(() => {
    if (
      currentOrganization &&
      hasSavedOrganizationDetails(currentOrganization)
    ) {
      setStep((currentStep) => (currentStep === 1 ? 2 : currentStep));
    }
  }, [currentOrganization]);

  const updateState = (update: Partial<OnboardingWizardState>) =>
    setWizardState((state) => ({ ...state, ...update }));

  const completeFounderOnboarding = useCallback(async () => {
    if (!currentOrganization || completionInFlight.current) return;
    completionInFlight.current = true;
    try {
      const completedOrganization =
        await organizationService.completeOnboarding(currentOrganization.id);
      setCurrentOrganization(completedOrganization);
      await refreshOrganizations();
      const { trackEvent } = await import("@/lib/analytics/posthog");
      trackEvent("pilot_activated", {});
      router.replace("/dashboard");
    } catch (error) {
      completionInFlight.current = false;
      toast.error(
        error instanceof Error
          ? error.message
          : "We could not finish onboarding. Please try again.",
      );
    }
  }, [
    currentOrganization,
    refreshOrganizations,
    router,
    setCurrentOrganization,
  ]);

  useEffect(() => {
    if (searchParams.get("payment") === "cancelled") {
      setStep(2);
    }
  }, [searchParams]);

  // A paid checkout returns to this page before the webhook has necessarily
  // persisted the subscription. Poll the server, then use the same guarded
  // completion path as the free-plan flow.
  useEffect(() => {
    const payment = searchParams.get("payment");
    const paymentOrganizationId = searchParams.get("organization_id");
    if (
      !currentOrganization ||
      payment !== "success" ||
      (paymentOrganizationId &&
        paymentOrganizationId !== currentOrganization.id)
    ) {
      return;
    }

    setStep(2);
    setPaymentState(null);
    let cancelled = false;
    let attempts = 0;
    let timer: ReturnType<typeof setTimeout> | null = null;

    const pollSubscription = async (): Promise<void> => {
      attempts += 1;
      try {
        const status = await billingService.getSubscriptionActivationStatus(
          currentOrganization.id,
        );
        if (cancelled) return;
        if (status.state === "active" || status.state === "trial") {
          await completeFounderOnboarding();
          return;
        }
      } catch {
        if (cancelled) return;
      }

      if (cancelled) return;
      if (attempts >= PAYMENT_POLL_LIMIT) {
        setPaymentState("failed");
        return;
      }
      timer = setTimeout(
        () => void pollSubscription(),
        PAYMENT_POLL_INTERVAL_MS,
      );
    };

    void pollSubscription();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [completeFounderOnboarding, currentOrganization, searchParams]);

  const handleStep1Next = async () => {
    if (!currentOrganization) return;
    setSaving(true);
    try {
      const industry = resolveIndustryValue(
        wizardState.industry,
        wizardState.customIndustry,
      );
      const updatedOrganization = await organizationService.updateOrganization(
        currentOrganization.id,
        {
          name: wizardState.businessName.trim(),
          slug: wizardState.slug.trim(),
          timezone: wizardState.timezone || null,
          website: wizardState.website.trim() || null,
          industry: industry || null,
          location: wizardState.location.trim() || null,
          business_details: wizardState.businessDescription.trim() || null,
        },
      );
      setCurrentOrganization(updatedOrganization);
      await refreshOrganizations();
      setStep(2);
    } catch (error) {
      toast.error(
        error instanceof Error
          ? error.message
          : "Failed to save organization details",
      );
    } finally {
      setSaving(false);
    }
  };

  const paymentQueryState = searchParams.get("payment");
  const visiblePaymentState =
    paymentQueryState === "cancelled" ? "cancelled" : paymentState;

  if (!currentOrganization) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center p-4">
      <div className="mb-8 text-center">
        <div className="mb-2 flex items-center justify-center gap-2">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-blue-600 to-cyan-600">
            <Phone className="h-5 w-5 text-white" />
          </div>
          <span className="text-xl font-bold">24x7 AI</span>
        </div>
        <h1 className="text-3xl font-bold text-gray-900">
          Welcome! Let&apos;s get you set up
        </h1>
      </div>

      <main className="w-full max-w-3xl">
        {step === 1 && (
          <StepOrgDetails
            organizationId={currentOrganization.id}
            state={wizardState}
            onChange={updateState}
            onNext={handleStep1Next}
            saving={saving}
          />
        )}
        {step === 2 && (
          <StepPlanSelection
            organizationId={currentOrganization.id}
            onActivated={() => void completeFounderOnboarding()}
            onBack={() => setStep(1)}
            paymentState={visiblePaymentState}
          />
        )}
      </main>

      <p className="mt-6 text-xs text-gray-400">
        You can configure agents, phone numbers, and integrations after your
        workspace is active.
      </p>
    </div>
  );
}
