/**
 * Utility functions for organization selection after authentication.
 */

import type { Organization } from "@/types/organization";

export interface SelectPreferredOrganizationOptions {
  /**
   * Organization the user just joined via invitation. Takes precedence over
   * a previously saved localStorage selection so invitees land in the invited
   * tenant even when they already belong to other orgs.
   */
  preferredOrganizationId?: string | null;
}

/**
 * Choose the current organization for a newly authenticated session.
 *
 * Priority:
 * 1. Invited organization (just joined)
 * 2. Previously saved selection (localStorage), when still a member
 * 3. First organization in the list
 *
 * @param organizations Organizations the user belongs to
 * @param savedOrgId Optional previously selected organization id
 * @param options Selection behavior flags
 * @returns Preferred organization, or null when the list is empty
 */
export function selectPreferredOrganization(
  organizations: Organization[],
  savedOrgId?: string | null,
  options?: SelectPreferredOrganizationOptions,
): Organization | null {
  if (organizations.length === 0) {
    return null;
  }

  const preferredId = options?.preferredOrganizationId;
  if (preferredId) {
    const invited = organizations.find((org) => org.id === preferredId);
    if (invited) {
      return invited;
    }
  }

  if (savedOrgId) {
    const saved = organizations.find((org) => org.id === savedOrgId);
    if (saved) {
      return saved;
    }
  }

  return organizations[0];
}
