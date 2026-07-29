"use client";

import React from "react";
import Link from "next/link";
import { ExternalLink } from "lucide-react";
import { DeleteConfirmationDialog } from "@/components/ui/delete-confirmation-dialog";
import {
  usePresetUsage,
  useDeletePreset,
} from "@/hooks/use-preset-queries";
import type { Preset, PresetUsageAgent } from "@/types/preset";

/**
 * PresetDeleteDialog — type-to-confirm delete wrapper for a voice-engine preset.
 *
 * Wraps the shared {@link DeleteConfirmationDialog}. On open it pre-fetches the
 * list of agents currently using the preset (via `usePresetUsage`):
 *  - In use: `warnings` carries the irreversible-action summary lines, and
 *    `extraContent` renders the affected agents as links to each agent's
 *    Properties tab (`/agents/{agentId}?tab=properties`) — where the preset
 *    picker lives — so the platform admin can navigate directly to review an
 *    agent before force-deleting. Agent names are links, not plain text, to
 *    make that review path one click away.
 *  - Not in use: no warnings and no extra content — the type-to-confirm gate
 *    ("Delete") still applies, so an accidental click on an unused preset still
 *    requires deliberate confirmation.
 *
 * On confirm it calls `useDeletePreset` with `force = count > 0`. The 409
 * `in_use` path is a backend safety net against the pre-fetch racing a new
 * assignment (or a direct API call): the error surfaces in the dialog so the
 * admin can retry with the now-visible usage warnings. A force-delete sets
 * `voice_agents.preset_id` to NULL via the FK, so every affected agent falls
 * back to the realtime default on its next call.
 */
export interface PresetDeleteDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Preset to delete. `null` is allowed so the parent can keep the dialog mounted. */
  preset: Preset | null;
  /** Fired after a successful delete (e.g. to refetch / clear the selected preset). */
  onDeleted?: () => void;
}

/**
 * Render the affected-agents list as navigable links to each agent's Properties
 * tab (where the preset picker lives).
 *
 * Links open in a NEW tab (`target="_blank"`) so the delete dialog stays open
 * underneath — the admin reviews the agent, closes the tab, and returns to
 * confirm or cancel the delete. New-tab also sidesteps the same-route no-op.
 */
function AffectedAgentsList({ agents }: { agents: PresetUsageAgent[] }) {
  return (
    <div className="space-y-1.5">
      <p className="font-medium">
        Used by {agents.length} agent{agents.length > 1 ? "s" : ""}:
      </p>
      <ul className="space-y-1">
        {agents.map((a) => (
          <li key={a.id} className="flex items-center gap-1.5">
            <ExternalLink className="h-3.5 w-3.5 flex-shrink-0 text-muted-foreground" />
            <Link
              href={`/agents/${a.id}?tab=properties`}
              target="_blank"
              rel="noopener noreferrer"
              className="text-primary underline underline-offset-2 hover:text-primary/80 break-all"
            >
              {a.name ?? a.id}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function PresetDeleteDialog({
  open,
  onOpenChange,
  preset,
  onDeleted,
}: PresetDeleteDialogProps) {
  const usageQuery = usePresetUsage(preset?.id ?? "", open);
  const deleteMutation = useDeletePreset();

  const count = usageQuery.data?.count ?? 0;
  const agents = usageQuery.data?.agents ?? [];

  // Summary lines only — the agent names live in `extraContent` as links so the
  // admin can jump straight to an agent's Properties tab to review before
  // deleting. A force-delete detaches the preset (preset_id -> NULL via the FK),
  // so each listed agent falls back to the realtime default on its next call.
  const warnings: string[] =
    count > 0
      ? [
          "Every agent listed below falls back to the default (Gemini Realtime) voice on its next call.",
          "This action cannot be undone.",
        ]
      : [];

  const handleDelete = async () => {
    if (!preset) return;
    // `force` lets the backend cascade-detach the using agents (preset_id ->
    // NULL). The pre-fetch already told the admin which agents lose the preset,
    // so when the preset is in use the confirm sends force=true after explicit
    // confirmation.
    await deleteMutation.mutateAsync({ presetId: preset.id, force: count > 0 });
    onDeleted?.();
    onOpenChange(false);
  };

  return (
    <DeleteConfirmationDialog
      open={open}
      onOpenChange={onOpenChange}
      itemName={preset?.name ?? ""}
      itemType="Voice Preset"
      warnings={warnings}
      extraContent={count > 0 ? <AffectedAgentsList agents={agents} /> : undefined}
      onDelete={handleDelete}
    />
  );
}