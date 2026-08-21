import { Save } from "lucide-react";

import { Button } from "@/components/ui/button";

interface AgentDetailSaveBarProps {
  /** Whether the current user may save agent configuration changes. */
  canEdit: boolean;
  /** Whether the save request is currently in progress. */
  saving: boolean;
  /** Persists the current agent form state. */
  onSave: () => void | Promise<void>;
}

/**
 * Renders the agent configuration save action independently from tab content.
 *
 * The agent detail page keeps editable form state alive while users move
 * between Persona and Settings. Rendering this action after the tabs makes
 * the save affordance available regardless of which tab is selected, while
 * still hiding it for read-only users.
 *
 * @param props - Save permission, request state, and persistence callback.
 * @returns A save action bar for editors, or `null` for read-only users.
 */
export function AgentDetailSaveBar({
  canEdit,
  saving,
  onSave,
}: AgentDetailSaveBarProps) {
  if (!canEdit) return null;

  return (
    <div className="flex justify-end" data-tour="agent-detail-save">
      <Button
        onClick={() => void onSave()}
        disabled={saving}
      >
        <Save className="h-4 w-4 mr-2" />
        {saving ? "Saving..." : "Save Changes"}
      </Button>
    </div>
  );
}
