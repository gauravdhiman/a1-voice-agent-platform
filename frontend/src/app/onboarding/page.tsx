"use client";

/**
 * Founder onboarding wizard page.
 *
 * Guides org admins through organization details, agent naming/template,
 * optional phone number, tools overview, and a final test-call step.
 */

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2, Phone } from "lucide-react";
import { toast } from "sonner";
import { SkipOnboardingButton } from "@/components/onboarding/skip-onboarding-button";
import { StepIndicator } from "@/components/onboarding/step-indicator";
import { StepOrgDetails } from "@/components/onboarding/step-org-details";
import { StepPhone } from "@/components/onboarding/step-phone";
import { StepTemplate } from "@/components/onboarding/step-template";
import { StepTest } from "@/components/onboarding/step-test";
import { StepTools } from "@/components/onboarding/step-tools";
import { useOrganization } from "@/contexts/organization-context";
import {
  canSkipOnboarding,
  parseIndustrySelection,
  resolveIndustryValue,
  suggestAgentName,
  type OnboardingWizardState,
} from "@/lib/onboarding";
import { suggestOrganizationSlugFromName } from "@/lib/organization-slug";
import { organizationService } from "@/services/organization-service";

export default function OnboardingPage() {
  const router = useRouter();
  const {
    currentOrganization,
    setCurrentOrganization,
    refreshOrganizations,
  } = useOrganization();
  const [step, setStep] = useState(1);
  const [saving, setSaving] = useState(false);
  const [skipping, setSkipping] = useState(false);

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
    businessDescription: "",
    agentName: suggestAgentName(currentOrganization?.name ?? ""),
    selectedTemplate: null,
    purchasedPhoneNumber: null,
    createdAgentId: null,
  }));

  // Redirect if already onboarded — except while the user is on the final
  // test step after the agent was just created (they may still want a test call).
  useEffect(() => {
    if (currentOrganization?.onboarding_completed && step !== 5) {
      router.replace("/dashboard");
    }
  }, [currentOrganization?.onboarding_completed, router, step]);

  // Sync org fields if the organization loads after the first paint.
  useEffect(() => {
    if (!currentOrganization) return;
    const parsed = parseIndustrySelection(currentOrganization.industry);
    setWizardState((s) => ({
      ...s,
      businessName: s.businessName || currentOrganization.name,
      slug: s.slug || currentOrganization.slug,
      timezone: s.timezone || currentOrganization.timezone || "",
      website: s.website || currentOrganization.website || "",
      industry: s.industry || parsed.selection,
      customIndustry: s.customIndustry || parsed.custom,
      location: s.location || currentOrganization.location || "",
      agentName: s.agentName || suggestAgentName(currentOrganization.name),
    }));
  }, [currentOrganization]);

  const updateState = (update: Partial<OnboardingWizardState>) =>
    setWizardState((s) => ({ ...s, ...update }));

  const markOnboardingCompletedLocally = () => {
    if (!currentOrganization) return;
    setCurrentOrganization({
      ...currentOrganization,
      onboarding_completed: true,
    });
  };

  const handleStep1Next = async () => {
    if (!currentOrganization) return;
    setSaving(true);
    try {
      const industry = resolveIndustryValue(
        wizardState.industry,
        wizardState.customIndustry,
      );
      await organizationService.updateOrganization(currentOrganization.id, {
        name: wizardState.businessName.trim(),
        slug: wizardState.slug.trim(),
        timezone: wizardState.timezone || null,
        website: wizardState.website.trim() || null,
        industry: industry || null,
        location: wizardState.location.trim() || null,
        business_details: wizardState.businessDescription.trim() || null,
      });
      await refreshOrganizations();
      if (!wizardState.agentName.trim()) {
        updateState({
          agentName: suggestAgentName(wizardState.businessName),
        });
      }
      setStep(2);
    } catch (err) {
      toast.error(
        err instanceof Error
          ? err.message
          : "Failed to save organization details",
      );
    } finally {
      setSaving(false);
    }
  };

  const handleComplete = () => {
    markOnboardingCompletedLocally();
    window.location.assign("/dashboard");
  };

  /**
   * Abandon the wizard before the final test step and open the dashboard.
   */
  const handleSkipOnboarding = async () => {
    if (!currentOrganization || skipping) return;
    setSkipping(true);
    const orgId = currentOrganization.id;
    markOnboardingCompletedLocally();
    try {
      await organizationService.completeOnboarding(orgId);
    } catch {
      toast.error("Couldn't save skip status, continuing to dashboard.");
    }
    window.location.assign("/dashboard");
  };

  if (!currentOrganization) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-4">
      <div className="text-center mb-8">
        <div className="flex items-center justify-center gap-2 mb-2">
          <div className="bg-gradient-to-br from-blue-600 to-cyan-600 w-10 h-10 rounded-xl flex items-center justify-center">
            <Phone className="w-5 h-5 text-white" />
          </div>
          <span className="text-xl font-bold">VoiceAI</span>
        </div>
        <h1 className="text-3xl font-bold text-gray-900">
          Welcome! Let&apos;s get you set up
        </h1>
        <p className="text-gray-500 mt-1">
          You&apos;re {Math.round(((step - 1) / 5) * 100)}% complete · Step{" "}
          {step} of 5
        </p>
      </div>

      <div className="w-full max-w-lg bg-white rounded-2xl shadow-xl p-8">
        <StepIndicator currentStep={step} />

        {step === 1 && (
          <StepOrgDetails
            state={wizardState}
            onChange={updateState}
            onNext={handleStep1Next}
            saving={saving}
          />
        )}
        {step === 2 && (
          <StepTemplate
            state={wizardState}
            onChange={updateState}
            onNext={() => setStep(3)}
            onSkip={() => {
              updateState({ selectedTemplate: null });
              setStep(3);
            }}
            onBack={() => setStep(1)}
          />
        )}
        {step === 3 && (
          <StepPhone
            state={wizardState}
            orgId={currentOrganization.id}
            onChange={updateState}
            onNext={() => setStep(4)}
            onBack={() => setStep(2)}
          />
        )}
        {step === 4 && (
          <StepTools onNext={() => setStep(5)} onBack={() => setStep(3)} />
        )}
        {step === 5 && (
          <StepTest
            state={wizardState}
            orgId={currentOrganization.id}
            onChange={updateState}
            onOnboardingCompleted={markOnboardingCompletedLocally}
            onComplete={handleComplete}
          />
        )}

        {canSkipOnboarding(step) && (
          <SkipOnboardingButton
            className="mt-6 pt-4 border-t border-gray-100"
            onSkip={handleSkipOnboarding}
            loading={skipping}
          />
        )}
      </div>

      <p className="text-xs text-gray-400 mt-6">
        You can always update these settings later from your dashboard.
      </p>
    </div>
  );
}
