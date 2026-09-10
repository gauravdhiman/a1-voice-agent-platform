"use client";

import React, { useState } from "react";
import { Star } from "lucide-react";
import { trackEvent } from "@/lib/analytics/posthog";
import { cn } from "@/lib/utils";

interface DemoFeedbackProps {
  /** Demo agent slug, recorded with the rating (no PII ever). */
  demoSlug: string;
}

/**
 * One-click 1–5 demo rating on the outcome page.
 *
 * Emits `demo_feedback` to PostHog (keyless-safe no-op without a key).
 * Rating-only by design: free-text feedback on a public demo page is a
 * PII and moderation liability. Detailed interest goes through the
 * request-demo form instead.
 */
export function DemoFeedback({ demoSlug }: DemoFeedbackProps) {
  const [rating, setRating] = useState<number | null>(null);

  function choose(value: number) {
    if (rating !== null) return;
    setRating(value);
    trackEvent("demo_feedback", { demo_slug: demoSlug, rating: value });
  }

  if (rating !== null) {
    return (
      <p
        className="text-sm text-slate-600"
        data-testid="demo-feedback-thanks"
      >
        Thanks — your rating helps us improve the demo.
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      <p className="text-sm font-medium text-slate-900">
        How was this demo?
      </p>
      <div className="flex items-center gap-1" role="group" aria-label="Rate this demo from 1 to 5">
        {[1, 2, 3, 4, 5].map((value) => (
          <button
            key={value}
            type="button"
            onClick={() => choose(value)}
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
