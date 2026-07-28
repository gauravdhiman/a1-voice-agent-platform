"use client";

import React from "react";
import Link from "next/link";
import { ExternalLink } from "lucide-react";
import { DeleteConfirmationDialog } from "@/components/ui/delete-confirmation-dialog";
import {
  usePlatformToolUsage,
  useDeletePlatformTool,
} from "@/hooks/use-agent-queries";
import type { PlatformTool, PlatformToolUsageAgent } from "@/types/agent";

/**
 * McpToolDeleteDialog — type-to-confirm delete wrapper for an MCP platform
 * tool (RFC §6.6 delete guardrails).
 *
 * Wraps the shared {@link DeleteConfirmationDialog}. On open it pre-fetches the
 * list of agents currently using the tool (via `usePlatformToolUsage`):
 *  - In use: `warnings` carries the irreversible-action summary lines, and
 *    `extraContent` renders the affected agents as links to each agent's Tools
 *    tab (`/agents/{agentId}?tab=tools`) so the platform admin can navigate
 *    directly to review an agent before force-deleting. Agent names are links,
 *    not plain text, to make that review path one click away.
 *  - Not in use: no warnings and no extra content — the type-to-confirm gate
 *    ("Delete") still applies, so an accidental click on an unused tool still
 *    requires deliberate confirmation.
 *
 * On confirm it calls `useDeletePlatformTool` with `force = count > 0`. The 409
 * `in_use` path is a backend safety net against the pre-fetch racing a new
 * attach (or a direct API call): the error surfaces in the dialog so the admin
 * can retry with the now-visible usage warnings.
 *
 * Native/legacy tools are never deletable (the backend refuses with 400) so
 * the Manage view does not render a delete affordance for them in the first
 * place — this dialog is MCP-only by construction.
 */
export interface McpToolDeleteDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Tool to delete. `null` is allowed so the parent can keep the dialog mounted. */
  tool: PlatformTool | null;
  /** Fired after a successful delete (e.g. to refetch / clear the selected tool). */
  onDeleted?: () => void;
}

/**
 * Render the affected-agents list as navigable links to each agent's Tools tab.
 *
 * The agent page reads `?tab=tools` on mount (`agents/[agentId]/page.tsx`), so a
 * link to `/agents/{agentId}?tab=tools` lands the admin directly on the Tools
 * tab where they can review the attachment before force-deleting. Links open in
 * a NEW tab (`target="_blank"`) so the delete dialog stays open underneath —
 * the admin reviews the agent, closes the tab, and returns to confirm or cancel
 * the delete. New-tab also sidesteps the same-route no-op: a link to the agent
 * the admin is already on does nothing in-tab, but opens fresh in a new tab.
 */
function AffectedAgentsList({ agents }: { agents: PlatformToolUsageAgent[] }) {
  return (
    <div className="space-y-1.5">
      <p className="font-medium">
        Used by {agents.length} agent{agents.length > 1 ? "s" : ""}:
      </p>
      <ul className="space-y-1">
        {agents.map((a) => (
          <li key={a.agent_id} className="flex items-center gap-1.5">
            <ExternalLink className="h-3.5 w-3.5 flex-shrink-0 text-muted-foreground" />
            <Link
              href={`/agents/${a.agent_id}?tab=tools`}
              target="_blank"
              rel="noopener noreferrer"
              className="text-primary underline underline-offset-2 hover:text-primary/80 break-all"
            >
              {a.agent_name ?? a.agent_id}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function McpToolDeleteDialog({
  open,
  onOpenChange,
  tool,
  onDeleted,
}: McpToolDeleteDialogProps) {
  const usageQuery = usePlatformToolUsage(tool?.id ?? "", open);
  const deleteMutation = useDeletePlatformTool();

  const count = usageQuery.data?.count ?? 0;
  const agents = usageQuery.data?.agents ?? [];

  // Summary lines only — the agent names live in `extraContent` as links so the
  // admin can jump straight to an agent's Tools tab to review before deleting.
  const warnings: string[] =
    count > 0
      ? [
          "Every agent listed below loses this tool on their next call.",
          "This action cannot be undone.",
        ]
      : [];

  const handleDelete = async () => {
    if (!tool) return;
    // `force` lets the backend cascade-detach the using agents' tool rows. The
    // pre-fetch already told the admin which agents lose the tool, so when the
    // tool is in use the confirm sends force=true after explicit confirmation.
    await deleteMutation.mutateAsync({ toolId: tool.id, force: count > 0 });
    onDeleted?.();
    onOpenChange(false);
  };

  return (
    <DeleteConfirmationDialog
      open={open}
      onOpenChange={onOpenChange}
      itemName={tool?.name ?? ""}
      itemType="MCP Server"
      warnings={warnings}
      extraContent={count > 0 ? <AffectedAgentsList agents={agents} /> : undefined}
      onDelete={handleDelete}
    />
  );
}