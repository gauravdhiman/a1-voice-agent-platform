/**
 * Helpers for creating a new skill from the Skills editor.
 *
 * Custom create only collects name / description / slug in a side sheet;
 * SKILL.md content is seeded with a minimal starter template so the user
 * finishes writing in the main editor (same path as editing any other skill).
 */

import { normalizeOrganizationSlug } from "@/lib/organization-slug";

/**
 * Suggest a kebab-case skill slug from a display name.
 *
 * @param name - Free-form skill display name
 * @returns Lowercase kebab-case slug (may be empty if name has no alphanumerics)
 *
 * @example
 * ```ts
 * suggestSkillSlugFromName("Appointment Booking") // "appointment-booking"
 * ```
 */
export function suggestSkillSlugFromName(name: string): string {
  return normalizeOrganizationSlug(name);
}

/**
 * Build a minimal starter SKILL.md body for a newly created skill.
 *
 * The API requires non-empty content (`min_length=1`). This template gives
 * the editor a useful skeleton without forcing the user to draft markdown
 * inside the create sheet.
 *
 * @param name - Skill display name used as the H1 title
 * @returns Markdown starter content
 *
 * @example
 * ```ts
 * buildStarterSkillMarkdown("Appointment Booking")
 * // "# Appointment Booking\n\n## When to use\n\n\n## Instructions\n\n"
 * ```
 */
export function buildStarterSkillMarkdown(name: string): string {
  const title = name.trim() || "Untitled Skill";
  return `# ${title}\n\n## When to use\n\n\n## Instructions\n\n`;
}
