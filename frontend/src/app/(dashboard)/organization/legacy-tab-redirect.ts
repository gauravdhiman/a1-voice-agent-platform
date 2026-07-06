/**
 * Pure helper: maps a legacy `?tab=...` value on /organization to the
 * new top-level route (N1 redirect). Returns `null` when no redirect
 * is needed and the page should render normally.
 *
 * Tested directly so the contract is locked in without rendering the
 * full 800-line OrganizationPage component.
 */
export type LegacyOrgTab = "overview" | "ai-agent" | "skills" | "phone-numbers";

/**
 * @param tab  The current `tab` search param (or null if absent).
 * @param orgId  The current org id. When missing the page renders
 *               AccessDenied and the redirect must NOT fire, so we
 *               return null here too.
 * @returns  The canonical target URL, or null when no redirect.
 */
export function legacyTabRedirect(
  tab: string | null,
  orgId: string | null,
): string | null {
  if (!tab || !orgId) return null;
  switch (tab) {
    case "phone-numbers":
      return `/phone-numbers?org_id=${encodeURIComponent(orgId)}`;
    case "skills":
      return `/skills?org_id=${encodeURIComponent(orgId)}`;
    case "ai-agent":
      return `/agents?org_id=${encodeURIComponent(orgId)}`;
    default:
      // `overview` or any unknown value -> render the org page as before.
      return null;
  }
}
