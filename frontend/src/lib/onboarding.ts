/**
 * Shared helpers and constants for the founder onboarding wizard.
 */

import type { VoiceTemplate } from "@/types/voice-template";
import { validateOrganizationSlug } from "@/lib/organization-slug";

/** Final required founder-onboarding step (plan activation). */
export const ONBOARDING_FINAL_STEP = 2;

/** Preset industries shown in the org-details step. */
export const ONBOARDING_INDUSTRIES = [
  { value: "dental", label: "Dental / Healthcare" },
  { value: "hvac", label: "HVAC / Heating & Cooling" },
  { value: "salon", label: "Salon & Spa" },
  { value: "real_estate", label: "Real Estate" },
  { value: "plumbing", label: "Plumbing" },
  { value: "electrical", label: "Electrical" },
  { value: "landscaping", label: "Landscaping" },
  { value: "cleaning", label: "Cleaning Services" },
  { value: "roofing", label: "Roofing" },
  { value: "other", label: "Other" },
] as const;

/** Known seed-template agent first names replaced by the user's agent name. */
const HARDCODED_TEMPLATE_AGENT_NAMES = [
  "Alex",
  "Jordan",
  "Taylor",
  "Morgan",
  "Casey",
] as const;

export interface OnboardingWizardState {
  /** Organization display name */
  businessName: string;
  /** URL slug for the organization */
  slug: string;
  /** IANA timezone (empty means unset) */
  timezone: string;
  /** Optional organization website URL */
  website: string;
  /** Selected industry value (preset key or custom text when Other) */
  industry: string;
  /** Free-text industry when the user picks Other */
  customIndustry: string;
  /** Business address / location */
  location: string;
  /** Optional longer business description */
  businessDescription: string;
  /** Display name for the voice agent */
  agentName: string;
  /** Selected use case template, or null when skipped */
  selectedTemplate: VoiceTemplate | null;
  /** Purchased phone number E.164, if any */
  purchasedPhoneNumber: string | null;
  /** Created agent id once step 5 succeeds */
  createdAgentId: string | null;
}

/**
 * Whether the user may abandon the founder onboarding flow.
 *
 * Founder onboarding requires both organization details and plan activation;
 * the page intentionally exposes no skip path because the dashboard contains
 * gated actions that depend on a selected plan.
 *
 * @param step Current 1-based wizard step
 * @returns True when a widget-level skip control should be shown
 */
export function canSkipOnboarding(step: number): boolean {
  void step;
  return false;
}

/**
 * Map a stored industry string into select value + optional custom text.
 *
 * Known preset values (except `other`) map directly. Anything else is treated
 * as a custom "Other" industry so the free-text field can be prefilled.
 *
 * @param industry Stored organization industry (may be null/empty)
 */
export function parseIndustrySelection(industry: string | null | undefined): {
  selection: string;
  custom: string;
} {
  if (!industry?.trim()) {
    return { selection: "", custom: "" };
  }
  const trimmed = industry.trim();
  const known = ONBOARDING_INDUSTRIES.find((item) => item.value === trimmed);
  if (known && known.value !== "other") {
    return { selection: known.value, custom: "" };
  }
  if (trimmed === "other") {
    return { selection: "other", custom: "" };
  }
  return { selection: "other", custom: trimmed };
}

/**
 * Resolve the industry value to persist from the step-1 form.
 *
 * When Other is selected, the trimmed custom text is stored so the org has a
 * meaningful industry label. Falls back to `"other"` if custom text is empty.
 *
 * @param selection Select value from the industry dropdown
 * @param customIndustry Free-text industry when selection is `other`
 */
export function resolveIndustryValue(
  selection: string,
  customIndustry: string,
): string {
  if (selection !== "other") {
    return selection.trim();
  }
  const custom = customIndustry.trim();
  return custom || "other";
}

/**
 * Whether step 1 (organization details) has all required fields.
 *
 * Required: org name, valid slug, timezone, industry (plus custom text when
 * Other), and business address.
 *
 * @param state Current wizard state
 */
export function isOrgDetailsStepComplete(state: {
  businessName: string;
  slug: string;
  timezone: string;
  industry: string;
  customIndustry: string;
  location: string;
}): boolean {
  if (!state.businessName.trim()) return false;
  if (validateOrganizationSlug(state.slug.trim()) !== null) return false;
  if (!state.timezone.trim()) return false;
  if (!state.industry.trim()) return false;
  if (state.industry === "other" && !state.customIndustry.trim()) return false;
  if (!state.location.trim()) return false;
  return true;
}

/**
 * Whether the user may continue from the template step with a selection.
 *
 * Agent name is required; a template must also be selected. Use
 * {@link canSkipTemplateStep} when leaving without a template.
 *
 * @param state Current wizard state
 */
export function canContinueTemplateStep(state: {
  agentName: string;
  selectedTemplate: VoiceTemplate | null;
}): boolean {
  return Boolean(state.agentName.trim() && state.selectedTemplate);
}

/**
 * Whether the user may skip template selection and continue.
 *
 * Only the agent name is required — templates are optional.
 *
 * @param state Current wizard state
 */
export function canSkipTemplateStep(state: { agentName: string }): boolean {
  return Boolean(state.agentName.trim());
}

/**
 * Normalize legacy template markers to the canonical dynamic-context syntax.
 *
 * This keeps old database rows and older template payloads compatible while
 * allowing edit screens to preserve runtime placeholders instead of resolving
 * them to the current user's values.
 *
 * @param text Template text that may contain legacy markers
 * @returns Text using canonical `{{org.*}}` and `{{agent.name}}` placeholders
 */
export function normalizeTemplatePlaceholders(
  text: string | null | undefined,
): string {
  if (!text) return "";

  let result = text
    .replace(/\[(?:Business|Company|Organization|Org) Name\]/gi, "{{org.name}}")
    .replace(/\[Agent Name\]/gi, "{{agent.name}}");

  result = result
    .replace(/\{\{\s*(?:org|organization|business|company)\.name\s*\}\}/gi, "{{org.name}}")
    .replace(/\{\{\s*(?:org|organization)\.industry\s*\}\}/gi, "{{org.industry}}")
    .replace(/\{\{\s*(?:org|organization)\.location\s*\}\}/gi, "{{org.location}}")
    .replace(/\{\{\s*(?:org|organization)\.business_details\s*\}\}/gi, "{{org.business_details}}")
    .replace(/\{\{\s*agent\.name\s*\}\}/gi, "{{agent.name}}");

  const namePattern = HARDCODED_TEMPLATE_AGENT_NAMES.join("|");
  result = result.replace(
    new RegExp(`\\bnamed (${namePattern})\\b`, "gi"),
    "named {{agent.name}}",
  );
  return result.replace(
    new RegExp(`\\bThis is (${namePattern})\\b`, "gi"),
    "This is {{agent.name}}",
  );
}

/**
 * Apply business/agent name placeholders to template text.
 *
 * Replaces canonical organization/agent name placeholders, legacy bracket
 * markers, and hard-coded seed names (Alex, Jordan, Taylor, Morgan, Casey) in
 * greetings and personas.
 *
 * @param text Template text that may contain placeholders or seed names
 * @param opts Names to substitute into the text
 * @returns Text with names applied (empty input returns empty string)
 */
export function applyTemplatePlaceholders(
  text: string | null | undefined,
  opts: { businessName: string; agentName: string },
): string {
  if (!text) return "";
  const businessName = opts.businessName.trim() || "Your Business";
  const agentName = opts.agentName.trim() || "your assistant";

  return normalizeTemplatePlaceholders(text)
    .replace(/\{\{org\.name\}\}/g, businessName)
    .replace(/\{\{agent\.name\}\}/g, agentName);
}

/**
 * Default agent display name suggested from the organization name.
 *
 * @param businessName Organization name
 */
export function suggestAgentName(businessName: string): string {
  const name = businessName.trim();
  if (!name) return "";
  return `${name} AI Agent`;
}
