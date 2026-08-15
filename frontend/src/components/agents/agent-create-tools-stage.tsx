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
        <h3 className="text-lg font-semibold mb-2">Business tools</h3>
        <p className="text-sm text-muted-foreground">
          Business tools help Lio take care of everyday tasks during calls.
          There&apos;s nothing to select right now — you can connect them after the
          agent is created.
        </p>
      </div>

      <div className="p-5 rounded-xl bg-slate-50 border border-slate-200 space-y-3">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-blue-100 flex items-center justify-center">
            <Plug className="w-5 h-5 text-blue-700" />
          </div>
          <div>
            <p className="font-semibold text-foreground">
              Ready to customize after setup
            </p>
            <p className="text-sm text-muted-foreground">
              No tools to select right now.
            </p>
          </div>
        </div>
        <ul className="text-sm text-muted-foreground list-disc pl-5 space-y-1">
          <li>Calendar and appointment booking</li>
          <li>Customer records and messaging</li>
          <li>Other business services your team uses</li>
        </ul>
      </div>

      <Alert>
        <AlertDescription className="text-sm">
          After creation, open the agent&apos;s <strong>Tools</strong> tab to
          choose the connections Lio should use.
        </AlertDescription>
      </Alert>
    </div>
  );
}
