"use client";

import React, { useState } from "react";
import { Star } from "lucide-react";
import { trackEvent } from "@/lib/analytics/posthog";
import { demoPublicService } from "@/services/demo-public-service";
import { cn } from "@/lib/utils";

interface DemoFeedbackProps {
  /** Demo agent slug, recorded with the rating (no PII ever). */
  demoSlug: string;
  /**
   * Short-lived receipt token binding the rating to the visitor's session.
   * When absent the rating still fires the analytics event but is not
   * stored in the platform.
   */
  receiptToken?: string | null;
}

/**
 * One-click 1–5 demo rating on the outcome page.
 *
 * Dual-write by design: the platform stores one row per session (visible
 * to platform admins) and a `demo_feedback` funnel event goes to PostHog
 * (keyless-safe no-op without a key). Rating-only: free-text feedback on
 * a public demo page is a PII and moderation liability. Detailed interest
 * goes through the request-demo form instead.
 */
export function DemoFeedback({ demoSlug, receiptToken }: DemoFeedbackProps) {
  const [rating, setRating] = useState<number | null>(null);

  async function choose(value: number) {
    if (rating !== null) return;
    setRating(value);
    trackEvent("demo_feedback", { demo_slug: demoSlug, rating: value });
    if (receiptToken) {
      try {
        await demoPublicService.submitDemoFeedback(
          demoSlug,
          receiptToken,
          value,
        );
      } catch {
        /* Analytics already captured the tap; a failed platform write
         * must not punish the visitor with an error state. */
      }
    }
  }

  if (rating !== null) {
    return (
      <p
        className="text-sm text-slate-600 dark:text-slate-300"
        data-testid="demo-feedback-thanks"
      >
        Thanks — your rating helps us improve the demo.
      </p>
    );
  }

  return (
    <div className="flex flex-wrap items-center justify-between gap-x-6 gap-y-3">
      <p className="text-sm font-medium text-slate-900 dark:text-white">
        How was this demo?
      </p>
      <div
        className="flex items-center gap-1"
        role="group"
        aria-label="Rate this demo from 1 to 5"
      >
        {[1, 2, 3, 4, 5].map((value) => (
          <button
            key={value}
            type="button"
            onClick={() => void choose(value)}
            aria-label={`Rate ${value} out of 5`}
            className={cn(
              "rounded-lg p-1.5 transition hover:bg-amber-100",
              "focus-visible:outline-2 focus-visible:outline-amber-500",
            )}
          >
            <Star className="h-6 w-6 text-amber-500" fill="currentColor" />
          </button>
        ))}
      </div>
    </div>
  );
}
