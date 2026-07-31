"use client";

import Link from "next/link";
import { MessageCircle, UserRound } from "lucide-react";
import { Button } from "@/components/ui/button";
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
      <Button asChild className="w-full h-11 text-base">
        <Link href={`/o/${slug}/call/${agent.id}`}>
          <MessageCircle className="mr-2 h-4 w-4" />
          Talk to this agent
        </Link>
      </Button>
    </article>
  );
}
