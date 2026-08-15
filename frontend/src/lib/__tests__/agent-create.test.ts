import { describe, expect, it } from "vitest";
import {
  isOptionalE164Phone,
  normalizeOptionalPhone,
  resolveAgentCreatePromptFields,
} from "@/lib/agent-create";

describe("isOptionalE164Phone", () => {
  it("allows empty phone numbers", () => {
    expect(isOptionalE164Phone("")).toBe(true);
    expect(isOptionalE164Phone("   ")).toBe(true);
    expect(isOptionalE164Phone(null)).toBe(true);
    expect(isOptionalE164Phone(undefined)).toBe(true);
  });

  it("accepts valid E.164 numbers", () => {
    expect(isOptionalE164Phone("+14155551234")).toBe(true);
    expect(isOptionalE164Phone("+441632960000")).toBe(true);
  });

  it("rejects non-E.164 values when provided", () => {
    expect(isOptionalE164Phone("4155551234")).toBe(false);
    expect(isOptionalE164Phone("+1")).toBe(false);
    expect(isOptionalE164Phone("not-a-phone")).toBe(false);
  });
});

describe("normalizeOptionalPhone", () => {
  it("returns null for blank values", () => {
    expect(normalizeOptionalPhone("")).toBeNull();
    expect(normalizeOptionalPhone("  ")).toBeNull();
  });

  it("returns trimmed phone when present", () => {
    expect(normalizeOptionalPhone("  +14155551234  ")).toBe("+14155551234");
  });
});

describe("resolveAgentCreatePromptFields", () => {
  it("defaults omitted custom instructions to an empty string", () => {
    const result = resolveAgentCreatePromptFields(
      {
        persona: "You are a receptionist.",
        mission: "Help callers at [Business Name].",
      },
      { businessName: "Acme Plumbing", agentName: "Riley" },
    );

    expect(result.custom_instructions).toBe("");
  });

  it("replaces template agent name placeholders before create", () => {
    const result = resolveAgentCreatePromptFields(
      {
        persona: "You are a receptionist named [Agent Name].",
        mission: "Help callers at [Business Name].",
        custom_instructions:
          "Default greeting: Thank you for calling [Business Name]! This is [Agent Name].",
      },
      { businessName: "Acme Plumbing", agentName: "Riley" },
    );

    expect(result.persona).toBe("You are a receptionist named Riley.");
    expect(result.mission).toBe("Help callers at Acme Plumbing.");
    expect(result.custom_instructions).toBe(
      "Default greeting: Thank you for calling Acme Plumbing! This is Riley.",
    );
  });

  it("resolves canonical agent and organization placeholders before create", () => {
    const result = resolveAgentCreatePromptFields(
      {
        persona: "You are the {{agent.name}} for {{org.name}}.",
        mission: "Help callers in {{org.industry}}.",
        custom_instructions: "Use the business context for {{org.name}}.",
      },
      { businessName: "Acme Plumbing", agentName: "Riley" },
    );

    expect(result.persona).toBe("You are the Riley for Acme Plumbing.");
    expect(result.mission).toBe("Help callers in {{org.industry}}.");
    expect(result.custom_instructions).toBe(
      "Use the business context for Acme Plumbing.",
    );
  });
});
