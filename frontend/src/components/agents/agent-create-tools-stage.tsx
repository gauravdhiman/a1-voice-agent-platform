"use client";

import { Plug } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";

/**
 * Informational platform-tools step for agent creation.
 *
 * No tools are selected here — association happens on the agent detail page
 * after the agent exists.
 */
export function AgentCreateToolsStage() {
  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold mb-2">Platform tools</h3>
        <p className="text-sm text-muted-foreground">
          Tools let your agent take real actions during calls. There is nothing
          to select on this step — you&apos;ll connect them after the agent is
          created.
        </p>
      </div>

      <div className="p-5 rounded-xl bg-slate-50 border border-slate-200 space-y-3">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-blue-100 flex items-center justify-center">
            <Plug className="w-5 h-5 text-blue-700" />
          </div>
          <div>
            <p className="font-semibold text-foreground">
              Informational only
            </p>
            <p className="text-sm text-muted-foreground">
              No tools to configure in this step.
            </p>
          </div>
        </div>
        <ul className="text-sm text-muted-foreground list-disc pl-5 space-y-1">
          <li>Google Calendar and booking integrations</li>
          <li>CRM and messaging connectors</li>
          <li>Custom MCP tools your organization publishes</li>
        </ul>
      </div>

      <Alert>
        <AlertDescription className="text-sm">
          After creation, open the agent&apos;s <strong>Tools</strong> tab to
          connect the integrations this agent should use.
        </AlertDescription>
      </Alert>
    </div>
  );
}
