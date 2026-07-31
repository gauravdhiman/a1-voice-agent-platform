/**
 * Helpers for organization URL slugs (used for `/o/{slug}` and API identifiers).
 */

const SLUG_PATTERN = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

const RESERVED_SLUGS = new Set([
  "api",
  "admin",
  "embed",
  "auth",
  "dashboard",
  "organization",
  "agents",
  "platform",
  "onboarding",
]);

/** Normalize free-form text into a lowercase kebab-case slug. */
export function normalizeOrganizationSlug(value: string): string {
  return value
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 100);
}

/** Suggest a slug from an organization name. */
export function suggestOrganizationSlugFromName(name: string): string {
  return normalizeOrganizationSlug(name);
}

/** Validate an organization slug for UI feedback. */
export function validateOrganizationSlug(value: string): string | null {
  if (!value.trim()) {
    return "Slug is required";
  }
  if (value.length > 100) {
    return "Slug must be 100 characters or fewer";
  }
  if (!SLUG_PATTERN.test(value)) {
    return "Use lowercase letters, numbers, and hyphens only (e.g. acme-support)";
  }
  if (RESERVED_SLUGS.has(value)) {
    return `'${value}' is reserved and cannot be used`;
  }
  return null;
}

/** Build the public page path for an organization slug. */
export function publicOrgPagePath(slug: string): string {
  return `/o/${slug}`;
}
