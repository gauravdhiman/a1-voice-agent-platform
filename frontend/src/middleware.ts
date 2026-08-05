import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

/**
 * Redirect any request that arrives on the Cloud Run default hostname
 * (*.run.app) to the branded custom domain so users never stay on the
 * Google-generated URL.
 */
export function middleware(request: NextRequest) {
  const host = (request.headers.get("host") || "").split(":")[0].toLowerCase();
  if (host.endsWith(".run.app")) {
    const url = request.nextUrl.clone();
    url.protocol = "https:";
    url.host = "www.247ai.live";
    url.port = "";
    return NextResponse.redirect(url, 308);
  }
  return NextResponse.next();
}

export const config = {
  // Skip Next.js internals and static assets — only redirect document/API navigations.
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
