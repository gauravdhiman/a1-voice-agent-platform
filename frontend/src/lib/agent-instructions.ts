/**
 * Shared helpers for the agent's four user-facing configuration fields.
 *
 * Agent role and communication style are stored as structured fields so they
 * remain easy to edit. The Markdown field is the single long-form instruction
 * document; this module keeps the managed identity section synchronized with
 * those structured values.
 */

import type { VoiceTemplate } from "@/types/voice-template";

/** Placeholder shown when an agent has no template-selected instructions yet. */
export const DEFAULT_AGENT_INSTRUCTIONS_PLACEHOLDER = `# Mission

Describe what this agent should help callers accomplish.

# Business Context

- **Business:** {{org.name}}
- **Industry:** {{org.industry}}
- **Location:** {{org.location}}

{{org.business_details}}

# Instructions

## How to help callers
1. Describe the steps this agent should follow.
2. Add any policies, escalation rules, or information it should share.

# After Hours

Describe what the agent should do outside business hours.`;

/** Convert onboarding placeholders into runtime Markdown template variables. */
function toRuntimeTemplateVariables(value: string): string {
  return value
    .replace(/\[Business Name\]/gi, "{{org.name}}")
    .replace(/\[Agent Name\]/gi, "{{agent.name}}");
}

/** Remove the managed identity section while preserving the user's content. */
function removeManagedIdentitySection(markdown: string): string {
  const lines = markdown.trim().split(/\r?\n/);
  const identityIndex = lines.findIndex((line) =>
    /^#\s+Identity and Persona\s*$/i.test(line.trim()),
  );

  if (identityIndex < 0) return markdown.trim();

  let sectionEnd = identityIndex + 1;
  while (sectionEnd < lines.length && !/^#\s+/.test(lines[sectionEnd])) {
    sectionEnd += 1;
  }

  lines.splice(identityIndex, sectionEnd - identityIndex);
  return lines.join("\n").trim();
}

/** Build the managed identity section from the structured role and style. */
function buildIdentitySection(role: string, tone: string): string {
  const normalizedRole = role.trim() || "a helpful AI voice assistant";
  const roleSentence = normalizedRole.replace(/[.!?]+$/, "");
  const identity = /\brepresenting\b/i.test(roleSentence)
    ? `${roleSentence}.`
    : `${roleSentence} representing {{org.name}}.`;
  const identityLine = /^you are\b/i.test(identity)
    ? identity
    : `You are ${identity}`;
  const toneLine = tone.trim()
    ? `Your communication style is ${tone.trim()}.`
    : "";

  return ["# Identity and Persona", identityLine, toneLine]
    .filter(Boolean)
    .join("\n\n");
}

/**
 * Convert a reusable use case template into the long-form Markdown field.
 *
 * Role and communication style stay in their dedicated fields. The template's
 * mission, business context, greeting, and instructions become Markdown content.
 */
export function buildMarkdownFromTemplate(
  template: Pick<
    VoiceTemplate,
    "mission" | "greeting" | "custom_instructions"
  >,
): string {
  const sections: string[] = [];

  if (template.mission) {
    sections.push(`# Mission\n\n${toRuntimeTemplateVariables(template.mission)}`);
  }

  sections.push(
    "# Business Context\n\n- **Business:** {{org.name}}\n- **Industry:** {{org.industry}}\n- **Location:** {{org.location}}\n\n{{org.business_details}}",
  );

  if (template.greeting) {
    sections.push(
      `# Default Greeting\n\n${toRuntimeTemplateVariables(template.greeting)}`,
    );
  }

  if (template.custom_instructions) {
    sections.push(
      `# Instructions\n\n${toRuntimeTemplateVariables(template.custom_instructions)}`,
    );
  }

  return sections.join("\n\n");
}

/**
 * Keep the structured role and style synchronized with the canonical Markdown.
 * Existing identity sections are replaced; all other user-authored Markdown is
 * preserved verbatim.
 */
export function buildAgentInstructionsMarkdown({
  role,
  tone,
  markdown,
}: {
  role: string;
  tone: string;
  markdown: string;
}): string {
  const content = removeManagedIdentitySection(markdown);
  const identity = buildIdentitySection(role, tone);
  return [identity, content].filter(Boolean).join("\n\n");
}
