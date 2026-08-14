"use client";

import Link from "next/link";
import { CheckCircle2, Plug, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";

export interface AgentCreateSuccessProps {
  /** Newly created agent id */
  agentId: string;
  /** Display name shown in the success heading */
  agentName: string;
}

/**
 * Post-create guidance with links to associate skills and tools.
 *
 * Shown after the agent create wizard finishes so users know where to finish
 * setup without being force-redirected away immediately.
 */
export function AgentCreateSuccess({
  agentId,
  agentName,
}: AgentCreateSuccessProps) {
  const skillsHref = `/agents/${agentId}?tab=skills`;
  const toolsHref = `/agents/${agentId}?tab=tools`;
  const agentHref = `/agents/${agentId}`;

  return (
    <div className="space-y-6 text-center" data-testid="agent-create-success">
      <div className="inline-flex items-center justify-center w-14 h-14 rounded-full bg-green-100">
        <CheckCircle2 className="h-7 w-7 text-green-700" />
      </div>

      <div className="space-y-2">
        <h3 className="text-xl font-semibold">
          {agentName} is ready
        </h3>
        <p className="text-sm text-muted-foreground max-w-md mx-auto">
          Your agent was created successfully. Next, add knowledge and connect
          business tools so it can answer questions and take action on calls.
        </p>
      </div>

      <div className="grid gap-3 text-left max-w-md mx-auto">
        <Link
          href={skillsHref}
          className="flex items-start gap-3 rounded-lg border p-4 hover:bg-muted/40 transition-colors"
          data-testid="agent-create-success-skills"
        >
          <div className="w-9 h-9 rounded-md bg-violet-100 flex items-center justify-center shrink-0">
            <Sparkles className="w-4 h-4 text-violet-700" />
          </div>
          <div>
            <p className="font-medium">Add knowledge</p>
            <p className="text-sm text-muted-foreground">
              Open the Skills tab to add the information this agent should use.
            </p>
          </div>
        </Link>

        <Link
          href={toolsHref}
          className="flex items-start gap-3 rounded-lg border p-4 hover:bg-muted/40 transition-colors"
          data-testid="agent-create-success-tools"
        >
          <div className="w-9 h-9 rounded-md bg-blue-100 flex items-center justify-center shrink-0">
            <Plug className="w-4 h-4 text-blue-700" />
          </div>
          <div>
            <p className="font-medium">Connect business tools</p>
            <p className="text-sm text-muted-foreground">
              Open the Tools tab to connect calendar, CRM, or other business
              services for this agent.
            </p>
          </div>
        </Link>
      </div>

      <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2">
        <Button asChild>
          <Link href={agentHref} data-testid="agent-create-success-view">
            View agent
          </Link>
        </Button>
        <Button asChild variant="outline">
          <Link href="/agents" data-testid="agent-create-success-list">
            Back to agents
          </Link>
        </Button>
      </div>
    </div>
  );
}
