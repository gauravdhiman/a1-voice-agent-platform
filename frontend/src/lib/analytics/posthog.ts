/**
 * Privacy-safe product analytics behind PostHog.
 *
 * Design rules (controlled-SaaS launch):
 * - Keyless-safe: every function is a no-op unless
 *   `NEXT_PUBLIC_POSTHOG_KEY` is set. Local/dev never emits.
 * - No PII ever: property keys that could carry identity
 *   (email, name, phone, …) are stripped before capture. Funnel
 *   properties are slugs, sources, and booleans only.
 * - Marketing/demo surfaces only: never instrument call-audio paths
 *   or authenticated dashboards with this module.
 *
 * @module lib/analytics/posthog
 */

import posthog from "posthog-js";

/** Funnel events with their allowed (PII-free) properties. */
export interface AnalyticsEvents {
  demo_played: { demo_slug: string };
  demo_completed: { demo_slug: string };
  demo_feedback: { demo_slug: string; rating: number };
  interest_submitted: { source: string; vertical?: string };
  invite_accepted: Record<string, never>;
  pilot_activated: Record<string, never>;
}

export type AnalyticsEventName = keyof AnalyticsEvents;

/** Property keys that must never leave the browser. */
const PII_KEYS = new Set([
  "email",
  "name",
  "first_name",
  "last_name",
  "phone",
  "business_name",
  "businessName",
  "message",
  "demoSlug",
]);

let initialized = false;

/**
 * Returns true when analytics can emit (browser + API key present).
 *
 * @returns Whether capture calls reach PostHog.
 */
export function isAnalyticsEnabled(): boolean {
  return (
    typeof window !== "undefined" &&
    Boolean(process.env.NEXT_PUBLIC_POSTHOG_KEY)
  );
}

/**
 * Initializes the PostHog client once. Safe to call repeatedly and
 * server-side (both no-op). Reads `NEXT_PUBLIC_POSTHOG_KEY` and
 * `NEXT_PUBLIC_POSTHOG_HOST` (defaults to US cloud).
 */
export function initAnalytics(): void {
  if (initialized || !isAnalyticsEnabled()) return;
  initialized = true;
  posthog.init(process.env.NEXT_PUBLIC_POSTHOG_KEY as string, {
    api_host: process.env.NEXT_PUBLIC_POSTHOG_HOST || "https://us.i.posthog.com",
    person_profiles: "identified_only",
    capture_pageview: false,
    capture_pageleave: false,
  });
}

/**
 * Removes PII-carrying keys from event properties.
 *
 * @param properties - Raw event properties.
 * @returns Sanitized copy safe for capture.
 */
export function sanitizeProperties(
  properties: Record<string, unknown>,
): Record<string, unknown> {
  const clean: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(properties)) {
    if (!PII_KEYS.has(key)) clean[key] = value;
  }
  return clean;
}

/**
 * Captures one funnel event (no-op unless initialized).
 *
 * @param event - Typed event name from `AnalyticsEvents`.
 * @param properties - PII-free properties (sanitized defensively).
 */
export function trackEvent<T extends AnalyticsEventName>(
  event: T,
  properties: AnalyticsEvents[T] = {} as AnalyticsEvents[T],
): void {
  if (!initialized || !isAnalyticsEnabled()) return;
  posthog.capture(event, sanitizeProperties(properties));
}

/**
 * Captures a pageview for the given path (no-op unless initialized).
 *
 * @param path - Route path without query string or tokens.
 */
export function trackPageview(path: string): void {
  if (!initialized || !isAnalyticsEnabled()) return;
  posthog.capture("$pageview", { $current_url: path });
}

/** Resets module state. Exported for tests only. */
export function __resetAnalyticsForTests(): void {
  initialized = false;
}
