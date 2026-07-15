/**
 * Pure helper: maps a legacy `?tab=...` value on /organization to the
 * new top-level route (N1 redirect). Returns `null` when no redirect
 * is needed and the page should render normally.
 *
 * Deep-link params are forwarded: a URL like
 * `/organization?tab=skills&skill=appointment-booking&file=references/faq.md`
 * redirects to `/skills?org_id=<id>&skill=...&file=...` so the SkillEditor
 * can restore the selected skill + file. The consumed `tab` param is NOT
 * forwarded; `org_id` is always re-emitted from the `orgId` arg.
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
 * @param searchParams  The page's current search params (from
 *               `useSearchParams()`). Every param except `tab` and
 *               `org_id` is forwarded onto the canonical route so deep
 *               links survive the redirect. May be omitted/null for
 *               callers that only care about the base contract.
 * @returns  The canonical target URL, or null when no redirect.
 */
export function legacyTabRedirect(
  tab: string | null,
  orgId: string | null,
  searchParams?: URLSearchParams | null,
): string | null {
  if (!tab || !orgId) return null;
  let base: string;
  switch (tab) {
    case "phone-numbers":
      base = "/phone-numbers";
      break;
    case "skills":
      base = "/skills";
      break;
    case "ai-agent":
      base = "/agents";
      break;
    default:
      // `overview` or any unknown value -> render the org page as before.
      return null;
  }
  // `org_id` is always first and uses encodeURIComponent to match the
  // historical encoding (`%20` for spaces, not `+`).
  let target = `${base}?org_id=${encodeURIComponent(orgId)}`;
  if (searchParams) {
    const extras = new URLSearchParams();
    searchParams.forEach((value, key) => {
      // `tab` is consumed by this redirect; `org_id` is re-emitted above.
      if (key !== "tab" && key !== "org_id") extras.set(key, value);
    });
    const extraStr = extras.toString();
    if (extraStr) target += `&${extraStr}`;
  }
  return target;
}
