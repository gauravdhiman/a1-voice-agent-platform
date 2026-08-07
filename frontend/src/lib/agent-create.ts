/**
 * Helpers for the multi-step agent creation widget.
 */

import { applyTemplatePlaceholders } from "@/lib/onboarding";

/** E.164 phone pattern used when a number is provided. */
export const AGENT_CREATE_E164_PHONE_REGEX = /^\+[1-9]\d{7,14}$/;

/** Prompt-related fields collected in the agent create wizard. */
export interface AgentCreatePromptFields {
  persona: string;
  mission: string;
  custom_instructions: string;
}

/**
 * Replace template placeholders in prompt fields using the final agent name.
 *
 * Templates are selected before the user enters a name, so persona/greeting copy
 * may still contain `[Agent Name]` or seed names until submit time.
 *
 * @param fields Prompt fields from the create form
 * @param opts Business and agent names to substitute
 */
export function resolveAgentCreatePromptFields(
  fields: AgentCreatePromptFields,
  opts: { businessName: string; agentName: string },
): AgentCreatePromptFields {
  return {
    persona: applyTemplatePlaceholders(fields.persona, opts),
    mission: applyTemplatePlaceholders(fields.mission, opts),
    custom_instructions: applyTemplatePlaceholders(fields.custom_instructions, opts),
  };
}

/**
 * Whether an optional phone field value is acceptable.
 *
 * Empty / whitespace-only values are allowed. Non-empty values must be E.164.
 *
 * @param value Raw phone input from the form
 */
export function isOptionalE164Phone(value: string | null | undefined): boolean {
  const trimmed = (value ?? "").trim();
  if (!trimmed) return true;
  return AGENT_CREATE_E164_PHONE_REGEX.test(trimmed);
}

/**
 * Normalize an optional phone field for the create-agent API payload.
 *
 * @param value Raw phone input from the form
 * @returns Trimmed E.164 string, or null when blank
 */
export function normalizeOptionalPhone(
  value: string | null | undefined,
): string | null {
  const trimmed = (value ?? "").trim();
  return trimmed || null;
}
