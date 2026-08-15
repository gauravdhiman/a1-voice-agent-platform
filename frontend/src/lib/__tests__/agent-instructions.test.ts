import { describe, expect, it } from "vitest";
import type { VoiceTemplate } from "@/types/voice-template";
import {
  DEFAULT_AGENT_INSTRUCTIONS_PLACEHOLDER,
  buildAgentInstructionsMarkdown,
  buildMarkdownFromTemplate,
} from "@/lib/agent-instructions";

const TEMPLATE: VoiceTemplate = {
  id: "template-1",
  name: "Dental Receptionist",
  industry: "dental",
  description: "A helpful dental receptionist.",
  persona: "You are a friendly dental receptionist named [Agent Name].",
  tone: "warm, professional, and reassuring",
  mission: "Help patients schedule appointments.",
  greeting: "Thank you for calling [Business Name]!",
  custom_instructions: "Always confirm appointment details.",
  is_active: true,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

describe("agent instruction helpers", () => {
  it("converts a voice template into markdown instruction content", () => {
    const markdown = buildMarkdownFromTemplate(TEMPLATE);

    expect(markdown).toContain("# Mission");
    expect(markdown).toContain("Help patients schedule appointments.");
    expect(markdown).toContain("# Default Greeting");
    expect(markdown).toContain("{{org.name}}");
    expect(markdown).toContain("# Procedures");
    expect(markdown).toContain("Always confirm appointment details.");
    expect(markdown).not.toContain("# Identity and Persona");
  });

  it("keeps role and communication style in the canonical markdown prompt", () => {
    const markdown = buildAgentInstructionsMarkdown({
      role: "Front Desk Coordinator",
      tone: "warm and professional",
      markdown: "# Mission\n\nHelp callers book appointments.",
    });

    expect(markdown).toContain("You are Front Desk Coordinator");
    expect(markdown).toContain("Your communication style is warm and professional.");
    expect(markdown).toContain("# Mission\n\nHelp callers book appointments.");
  });

  it("replaces an existing identity section when role or style changes", () => {
    const markdown = buildAgentInstructionsMarkdown({
      role: "Billing Specialist",
      tone: "concise",
      markdown:
        "# Identity and Persona\n\nYou are an old role.\nYour communication style is old.\n\n# Mission\n\nAnswer billing questions.",
    });

    expect(markdown).toContain("You are Billing Specialist");
    expect(markdown).toContain("Your communication style is concise.");
    expect(markdown).not.toContain("old role");
    expect(markdown).toContain("# Mission\n\nAnswer billing questions.");
  });

  it("provides a markdown placeholder without duplicating role or style fields", () => {
    expect(DEFAULT_AGENT_INSTRUCTIONS_PLACEHOLDER).toContain("# Mission");
    expect(DEFAULT_AGENT_INSTRUCTIONS_PLACEHOLDER).toContain("# Procedures");
    expect(DEFAULT_AGENT_INSTRUCTIONS_PLACEHOLDER).not.toContain(
      "# Identity and Persona",
    );
  });
});
