"use client";

import { ChevronRight, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  ONBOARDING_INDUSTRIES,
  isOrgDetailsStepComplete,
  type OnboardingWizardState,
} from "@/lib/onboarding";
import {
  normalizeOrganizationSlug,
  suggestOrganizationSlugFromName,
  validateOrganizationSlug,
} from "@/lib/organization-slug";
import {
  ORGANIZATION_TIMEZONE_OPTIONS,
  ORGANIZATION_TIMEZONE_UNSET,
} from "@/lib/organization-timezones";

export interface StepOrgDetailsProps {
  state: OnboardingWizardState;
  onChange: (update: Partial<OnboardingWizardState>) => void;
  onNext: () => void;
  saving: boolean;
}

/**
 * Step 1 — organization profile details for founder onboarding.
 *
 * Collects name, slug, timezone, website, industry, address, and an optional
 * description. Continue stays disabled until required fields are valid.
 */
export function StepOrgDetails({
  state,
  onChange,
  onNext,
  saving,
}: StepOrgDetailsProps) {
  const canProceed = isOrgDetailsStepComplete(state);
  const slugError = state.slug.trim()
    ? validateOrganizationSlug(state.slug.trim())
    : null;
  const timezoneOptions = ORGANIZATION_TIMEZONE_OPTIONS.filter(
    (option) => option.value !== ORGANIZATION_TIMEZONE_UNSET,
  );

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">
          Organization details
        </h2>
        <p className="text-gray-500 mt-1">
          Tell us about your organization so we can personalize your workspace.
        </p>
      </div>

      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Organization name <span className="text-red-500">*</span>
          </label>
          <Input
            placeholder="e.g. Smith Plumbing Co."
            value={state.businessName}
            onChange={(e) => {
              const businessName = e.target.value;
              const suggested = suggestOrganizationSlugFromName(businessName);
              const currentNormalized = normalizeOrganizationSlug(
                state.businessName,
              );
              const shouldSyncSlug =
                !state.slug.trim() || state.slug === currentNormalized;
              onChange({
                businessName,
                ...(shouldSyncSlug && suggested ? { slug: suggested } : {}),
              });
            }}
            data-testid="onboarding-org-name"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Slug <span className="text-red-500">*</span>
          </label>
          <Input
            placeholder="e.g. smith-plumbing"
            value={state.slug}
            onChange={(e) =>
              onChange({ slug: normalizeOrganizationSlug(e.target.value) })
            }
            data-testid="onboarding-org-slug"
          />
          {slugError ? (
            <p className="text-xs text-red-600 mt-1">{slugError}</p>
          ) : (
            <p className="text-xs text-gray-400 mt-1">
              Used in your public page URL: /o/{state.slug || "your-slug"}
            </p>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Timezone <span className="text-red-500">*</span>
          </label>
          <Select
            value={state.timezone ? state.timezone : undefined}
            onValueChange={(timezone) => onChange({ timezone })}
          >
            <SelectTrigger data-testid="onboarding-org-timezone">
              <SelectValue placeholder="Select timezone" />
            </SelectTrigger>
            <SelectContent>
              {timezoneOptions.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Website
          </label>
          <Input
            type="url"
            placeholder="https://www.example.com"
            value={state.website}
            onChange={(e) => onChange({ website: e.target.value })}
            data-testid="onboarding-org-website"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Industry <span className="text-red-500">*</span>
          </label>
          <Select
            value={state.industry || undefined}
            onValueChange={(industry) =>
              onChange({
                industry,
                customIndustry:
                  industry === "other" ? state.customIndustry : "",
              })
            }
          >
            <SelectTrigger data-testid="onboarding-org-industry">
              <SelectValue placeholder="Select your industry" />
            </SelectTrigger>
            <SelectContent>
              {ONBOARDING_INDUSTRIES.map((ind) => (
                <SelectItem key={ind.value} value={ind.value}>
                  {ind.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {state.industry === "other" && (
            <Input
              className="mt-2"
              placeholder="Enter your industry"
              value={state.customIndustry}
              onChange={(e) => onChange({ customIndustry: e.target.value })}
              data-testid="onboarding-org-industry-other"
            />
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Business location / address <span className="text-red-500">*</span>
          </label>
          <Input
            placeholder="e.g. 123 Main St, Suite 200, Austin, TX 78701"
            value={state.location}
            onChange={(e) => onChange({ location: e.target.value })}
            data-testid="onboarding-org-address"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Brief business description
          </label>
          <Textarea
            placeholder="Describe your services, hours, and anything the AI should know about your business..."
            value={state.businessDescription}
            onChange={(e) => onChange({ businessDescription: e.target.value })}
            rows={3}
          />
        </div>
      </div>

      <Button
        onClick={onNext}
        disabled={!canProceed || saving}
        className="w-full"
        size="lg"
        data-testid="onboarding-org-continue"
      >
        {saving ? (
          <>
            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            Saving...
          </>
        ) : (
          <>
            Continue <ChevronRight className="w-4 h-4 ml-2" />
          </>
        )}
      </Button>
    </div>
  );
}
