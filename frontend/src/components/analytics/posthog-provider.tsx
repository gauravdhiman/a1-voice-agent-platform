"use client";

import { useEffect } from "react";
import { usePathname } from "next/navigation";
import { initAnalytics, trackPageview } from "@/lib/analytics/posthog";

interface AnalyticsProviderProps {
  children: React.ReactNode;
}

/**
 * Initializes PostHog once and records a pageview per route change.
 *
 * Renders nothing. Keyless-safe: without `NEXT_PUBLIC_POSTHOG_KEY`
 * nothing initializes and no traffic leaves the browser.
 */
export function AnalyticsProvider({ children }: AnalyticsProviderProps) {
  const pathname = usePathname();

  useEffect(() => {
    initAnalytics();
  }, []);

  useEffect(() => {
    if (pathname) trackPageview(pathname);
  }, [pathname]);

  return <>{children}</>;
}
