import { describe, expect, it } from "vitest";
import { applicationSecurityHeaders } from "../security-headers";

describe("application security headers", () => {
  it("keeps microphone access and embeds while isolating authenticated pages", () => {
    const rules = applicationSecurityHeaders(true);
    const common = Object.fromEntries(rules[0].headers.map((h) => [h.key, h.value]));
    expect(common["Permissions-Policy"]).toContain("microphone=(self)");
    expect(common["Strict-Transport-Security"]).toContain("max-age=31536000");
    expect(common["X-Frame-Options"]).toBeUndefined();
    expect(common["Content-Security-Policy"]).not.toContain("connect-src");
    expect(common["Content-Security-Policy"]).toContain("frame-ancestors 'self'");
    expect(rules.find((r) => r.source === "/embed/:path*")?.headers).toContainEqual({ key: "Content-Security-Policy", value: "object-src 'none'; base-uri 'self'; frame-ancestors *" });
    expect(rules.find((r) => r.source === "/auth/:path*")?.headers).toContainEqual({ key: "X-Frame-Options", value: "DENY" });
  });
  it("does not pin localhost to HTTPS", () => {
    expect(applicationSecurityHeaders(false)[0].headers.some((h) => h.key === "Strict-Transport-Security")).toBe(false);
  });
});
