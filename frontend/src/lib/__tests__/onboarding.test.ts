import { describe, expect, it } from "vitest";
import {
  ONBOARDING_FINAL_STEP,
  applyTemplatePlaceholders,
  canContinueTemplateStep,
  canSkipOnboarding,
  canSkipTemplateStep,
  isOrgDetailsStepComplete,
  parseIndustrySelection,
  resolveIndustryValue,
  suggestAgentName,
} from "@/lib/onboarding";
import type { VoiceTemplate } from "@/types/voice-template";

const baseOrgDetails = {
  businessName: "Acme Plumbing",
  slug: "acme-plumbing",
  timezone: "America/New_York",
  industry: "plumbing",
  customIndustry: "",
  location: "123 Main St, Austin, TX 78701",
};

describe("canSkipOnboarding", () => {
  it("allows skip on every step before the final test step", () => {
    for (let step = 1; step < ONBOARDING_FINAL_STEP; step += 1) {
      expect(canSkipOnboarding(step)).toBe(true);
    }
  });

  it("does not allow skip on the final test step", () => {
    expect(canSkipOnboarding(ONBOARDING_FINAL_STEP)).toBe(false);
  });

  it("does not allow skip for invalid steps", () => {
    expect(canSkipOnboarding(0)).toBe(false);
    expect(canSkipOnboarding(-1)).toBe(false);
  });
});

describe("isOrgDetailsStepComplete", () => {
  it("requires name, slug, timezone, industry, and address", () => {
    expect(isOrgDetailsStepComplete(baseOrgDetails)).toBe(true);
    expect(
      isOrgDetailsStepComplete({ ...baseOrgDetails, businessName: "  " }),
    ).toBe(false);
    expect(isOrgDetailsStepComplete({ ...baseOrgDetails, slug: "Bad Slug" })).toBe(
      false,
    );
    expect(isOrgDetailsStepComplete({ ...baseOrgDetails, timezone: "" })).toBe(
      false,
    );
    expect(isOrgDetailsStepComplete({ ...baseOrgDetails, industry: "" })).toBe(
      false,
    );
    expect(isOrgDetailsStepComplete({ ...baseOrgDetails, location: "" })).toBe(
      false,
    );
  });

  it("requires custom industry text when Other is selected", () => {
    expect(
      isOrgDetailsStepComplete({
        ...baseOrgDetails,
        industry: "other",
        customIndustry: "",
      }),
    ).toBe(false);
    expect(
      isOrgDetailsStepComplete({
        ...baseOrgDetails,
        industry: "other",
        customIndustry: "Veterinary",
      }),
    ).toBe(true);
  });
});

describe("industry helpers", () => {
  it("resolves Other to the custom industry text", () => {
    expect(resolveIndustryValue("plumbing", "")).toBe("plumbing");
    expect(resolveIndustryValue("other", "  Veterinary Clinic ")).toBe(
      "Veterinary Clinic",
    );
    expect(resolveIndustryValue("other", "  ")).toBe("other");
  });

  it("parses stored industries back into select + custom fields", () => {
    expect(parseIndustrySelection("dental")).toEqual({
      selection: "dental",
      custom: "",
    });
    expect(parseIndustrySelection("Veterinary Clinic")).toEqual({
      selection: "other",
      custom: "Veterinary Clinic",
    });
    expect(parseIndustrySelection(null)).toEqual({ selection: "", custom: "" });
  });
});

describe("template step gating", () => {
  const template = { id: "t1", name: "Dental Receptionist" } as VoiceTemplate;

  it("requires agent name and a template to continue", () => {
    expect(
      canContinueTemplateStep({ agentName: "Alex", selectedTemplate: template }),
    ).toBe(true);
    expect(
      canContinueTemplateStep({ agentName: "", selectedTemplate: template }),
    ).toBe(false);
    expect(
      canContinueTemplateStep({ agentName: "Alex", selectedTemplate: null }),
    ).toBe(false);
  });

  it("allows skipping templates when an agent name is set", () => {
    expect(canSkipTemplateStep({ agentName: "Front Desk" })).toBe(true);
    expect(canSkipTemplateStep({ agentName: "  " })).toBe(false);
  });
});

describe("applyTemplatePlaceholders", () => {
  it("replaces business and agent name placeholders", () => {
    const text =
      "Thank you for calling [Business Name]! This is [Agent Name], how can I help?";
    expect(
      applyTemplatePlaceholders(text, {
        businessName: "Acme",
        agentName: "Riley",
      }),
    ).toBe("Thank you for calling Acme! This is Riley, how can I help?");
  });

  it("replaces hard-coded seed agent names in greetings and personas", () => {
    const greeting =
      "Thank you for calling [Business Name]! This is Alex, how can I help you today?";
    const persona =
      "You are a friendly dental receptionist named Alex. You help patients.";

    expect(
      applyTemplatePlaceholders(greeting, {
        businessName: "Smile Dental",
        agentName: "Sam",
      }),
    ).toBe(
      "Thank you for calling Smile Dental! This is Sam, how can I help you today?",
    );
    expect(
      applyTemplatePlaceholders(persona, {
        businessName: "Smile Dental",
        agentName: "Sam",
      }),
    ).toBe(
      "You are a friendly dental receptionist named Sam. You help patients.",
    );
  });
});

describe("suggestAgentName", () => {
  it("builds a default agent name from the organization name", () => {
    expect(suggestAgentName("Acme Plumbing")).toBe("Acme Plumbing AI Agent");
    expect(suggestAgentName("  ")).toBe("");
  });
});
