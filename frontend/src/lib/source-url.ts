/**
 * Return the current browser page as a privacy-preserving call source.
 *
 * Query strings and fragments are not needed to identify the page and may
 * contain campaign identifiers or user data, so they are omitted before the
 * URL is sent to the call-token endpoint.
 */
export function getCurrentPageSourceUrl(): string | null {
  if (typeof window === "undefined") return null;

  try {
    const url = new URL(window.location.href);
    url.username = "";
    url.password = "";
    url.search = "";
    url.hash = "";
    return url.toString();
  } catch {
    return null;
  }
}
