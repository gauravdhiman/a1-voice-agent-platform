"use client";

import Link from "next/link";
import { MessageCircle, UserRound } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DEMO_TRIAL_EXHAUSTED_MESSAGE,
  formatDemoCallsRemaining,
  formatDemoDuration,
  isDemoCallLimitReached,
} from "@/lib/demo-call-limits";
import type { PublicAgentSummary } from "@/types/public-org-page";

/**
 * Mobile-friendly card for a published agent on the public org page.
 */
export interface PublicAgentCardProps {
  slug: string;
  agent: PublicAgentSummary;
}

export function PublicAgentCard({ slug, agent }: PublicAgentCardProps) {
  const subtitle = agent.persona || agent.mission;
  const isExhausted =
    agent.is_demo && isDemoCallLimitReached(agent.demo_calls_remaining);
  const callLimit = agent.is_demo
    ? formatDemoCallsRemaining(agent.demo_calls_remaining)
    : null;
  const durationLimit = agent.is_demo
    ? formatDemoDuration(agent.demo_max_call_duration_seconds)
    : null;

  return (
    <article className="flex flex-col gap-4 rounded-2xl border bg-card p-5 shadow-sm">
      <div className="flex items-start gap-3">
        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
          <UserRound className="h-5 w-5" />
        </div>
        <div className="min-w-0 flex-1">
          <h3 className="text-lg font-semibold leading-tight">{agent.name}</h3>
          {subtitle ? (
            <p className="mt-1 line-clamp-3 text-sm text-muted-foreground">
              {subtitle}
            </p>
          ) : null}
        </div>
      </div>
      {agent.is_demo ? (
        <div className="space-y-2 rounded-lg border border-amber-200 bg-amber-50/70 p-3 text-xs text-amber-950">
          <div className="font-medium">Demo agent</div>
          {!isExhausted ? (
            <div className="space-y-1 text-amber-800">
              {callLimit ? <div>Calls: {callLimit}</div> : null}
              {durationLimit ? <div>Duration: {durationLimit}</div> : null}
            </div>
          ) : null}
          {isExhausted ? (
            <p className="text-xs text-amber-900">
              {DEMO_TRIAL_EXHAUSTED_MESSAGE}
            </p>
          ) : null}
        </div>
      ) : null}
      {isExhausted ? (
        <Button className="h-11 w-full text-base" disabled>
          Demo unavailable
        </Button>
      ) : (
        <Button asChild className="h-11 w-full text-base">
          <Link href={`/o/${slug}/call/${agent.id}`}>
            <MessageCircle className="mr-2 h-4 w-4" />
            Talk to this agent
          </Link>
        </Button>
      )}
    </article>
  );
}
