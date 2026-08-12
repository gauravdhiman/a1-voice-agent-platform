/**
 * Shared helpers for tabbed views that persist the selected tab in the URL.
 *
 * Keeping tab resolution and URL construction in one place makes deep links
 * predictable across the dashboard while preserving unrelated query state.
 */

/**
 * Resolves a URL value to one of the supported tabs.
 *
 * @param value - The raw value read from the `tab` query parameter.
 * @param allowedTabs - The tab values supported by the current view.
 * @param fallback - The tab to display when the URL is missing or invalid.
 * @returns A supported tab value.
 */
export function resolveTab<T extends string>(
  value: string | null,
  allowedTabs: readonly T[],
  fallback: T,
): T {
  return value && allowedTabs.includes(value as T) ? (value as T) : fallback;
}

/**
 * Builds a tab deep link while preserving the current query parameters.
 *
 * The default tab is omitted to keep the canonical URL short. Non-default
 * tabs are written as `?tab=...` so they can be copied, refreshed, or opened
 * directly by another user.
 *
 * @param pathname - The route pathname for the tabbed view.
 * @param currentSearch - The current query string without the leading `?`.
 * @param tab - The tab that should be active at the destination.
 * @param defaultTab - The tab rendered when no tab parameter is present.
 * @returns A pathname with the updated query string.
 */
export function buildTabHref(
  pathname: string,
  currentSearch: string,
  tab: string,
  defaultTab: string,
): string {
  const params = new URLSearchParams(currentSearch);

  if (tab === defaultTab) {
    params.delete("tab");
  } else {
    params.set("tab", tab);
  }

  const query = params.toString();
  return query ? `${pathname}?${query}` : pathname;
}
