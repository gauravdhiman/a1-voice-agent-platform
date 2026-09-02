import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { SITE_HOST } from "@/lib/site-config";

const APEX_HOST = "247ai.live";
const RUN_APP_HOST_SUFFIX = ".run.app";

function normalizeHost(host: string): string {
  return host.trim().toLowerCase().replace(/\.$/, "").split(":")[0];
}

/**
 * Returns whether a request host must be redirected to the canonical site
 * host. Cloud Run's generated hostname is included so it cannot become an
 * indexable duplicate of the branded domain.
 */
export function shouldRedirectToCanonicalHost(host: string): boolean {
  const normalizedHost = normalizeHost(host);
  return (
    normalizedHost === APEX_HOST ||
    normalizedHost.endsWith(RUN_APP_HOST_SUFFIX)
  );
}

/**
 * Redirect apex and Cloud Run default-host requests to the branded custom
 * domain so every URL has one indexable host.
 */
export function middleware(request: NextRequest) {
  const host = request.headers.get("host") || request.nextUrl.hostname;
  if (shouldRedirectToCanonicalHost(host)) {
    const url = request.nextUrl.clone();
    url.protocol = "https:";
    url.hostname = SITE_HOST;
    url.port = "";
    return NextResponse.redirect(url, 308);
  }
  return NextResponse.next();
}

export const config = {
  // Skip Next.js internals and static assets — only redirect document/API navigations.
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
