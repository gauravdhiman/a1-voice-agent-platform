"use client";

import { useEffect } from "react";
import { usePathname } from "next/navigation";

type AnalyticsModule = typeof import("@/lib/analytics/posthog");

let analyticsModulePromise: Promise<AnalyticsModule> | null = null;

function loadAnalytics(): Promise<AnalyticsModule> {
  analyticsModulePromise ??= import("@/lib/analytics/posthog");
  return analyticsModulePromise;
}

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
  const analyticsEnabled = Boolean(process.env.NEXT_PUBLIC_POSTHOG_KEY);

  useEffect(() => {
    if (!analyticsEnabled) return;

    let isCurrentPath = true;
    void loadAnalytics()
      .then(async ({ initAnalytics, trackPageview }) => {
        await initAnalytics();
        if (isCurrentPath) {
          trackPageview(pathname || window.location.pathname);
        }
      })
      .catch(() => {
        // Analytics is optional; initialization failures must not affect the app.
      });

    return () => {
      isCurrentPath = false;
    };
  }, [analyticsEnabled, pathname]);

  return <>{children}</>;
}
