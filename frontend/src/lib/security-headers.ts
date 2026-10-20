/** HTTP header configuration preserving voice embeds and external sign-in. */
export function applicationSecurityHeaders(production: boolean) {
  const common = [
    { key: "X-Content-Type-Options", value: "nosniff" },
    { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
    { key: "Permissions-Policy", value: "camera=(), microphone=(self), geolocation=()" },
    { key: "Content-Security-Policy", value: "object-src 'none'; base-uri 'self'; frame-ancestors 'self'" },
  ];
  if (production) common.push({ key: "Strict-Transport-Security", value: "max-age=31536000; includeSubDomains" });
  return [
    { source: "/:path*", headers: common },
    // Customer-hosted call iframes are an intentional product surface. The
    // backend separately enforces each agent's permitted request origins.
    { source: "/embed/:path*", headers: [{ key: "Content-Security-Policy", value: "object-src 'none'; base-uri 'self'; frame-ancestors *" }] },
    ...["auth", "dashboard", "platform", "organization", "agents", "calls"].map((path) => ({
      source: `/${path}/:path*`,
      headers: [{ key: "X-Frame-Options", value: "DENY" }, { key: "Content-Security-Policy", value: "object-src 'none'; base-uri 'self'; frame-ancestors 'none'" }],
    })),
  ];
}
