"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Loader2, Plus, SlidersHorizontal, Upload, Pencil, Trash2 } from "lucide-react";
import type { Preset } from "@/types/preset";
import {
  usePresets,
  useCreatePreset,
  useUpdatePreset,
  usePublishPreset,
} from "@/hooks/use-preset-queries";
import { PresetConfigForm } from "@/components/presets/preset-config-form";
import { PresetDeleteDialog } from "@/components/presets/preset-delete-dialog";

/**
 * PlatformPresetsManager — inline platform-admin surface for the voice-engine
 * preset catalog (`/platform/presets`). Mirrors
 * `platform-tools-manager.tsx`: a two-view inline toggle (manage list / author
 * form), plain `.map()` row-cards with `Badge` Published/Draft + type badge +
 * Publish/Unpublish + Edit + Delete buttons. No DataTable.
 *
 * A platform admin authors a preset's `SpeechConfig` here (the power-user
 * surface — the admin DOES see engine/stage fields; only the org user is
 * shielded via the agent picker). "Save draft" persists `is_published=false`;
 * "Publish" persists `is_published=true`. Both are gated on a valid config
 * (the `PresetConfigForm` reports validity — invalid `params` JSON blocks
 * submit). The backend re-validates the discriminated union on write
 * (`extra="forbid"`), so a 400 surfaces inline.
 *
 * Two views share one panel (inline toggle — no Sheet/drawer):
 *  - **Author / edit preset** (`view === "author"`): name + description +
 *    `<PresetConfigForm/>` + "Save draft" / "Publish". In edit mode
 *    (`editingId` set) the form is seeded from the selected preset and submit
 *    issues `PUT /{id}`; otherwise `POST /` (upsert by name). On success the
 *    form resets and the manage list refetches.
 *  - **Manage existing presets** (`view === "manage"`): lists drafts +
 *    published presets with publish/unpublish, edit, and delete actions.
 *
 * Conventions match `platform-tools-manager.tsx`: plain useState, no
 * react-hook-form, no window.* dialogs.
 */
export interface PlatformPresetsManagerProps {
  /** Initial view shown when the panel mounts. Defaults to "manage". */
  initialView?: "author" | "manage";
}

type View = "author" | "manage";

export function PlatformPresetsManager({
  initialView = "manage",
}: PlatformPresetsManagerProps) {
  const [view, setView] = React.useState<View>(initialView);

  // Author form state. `editingId` is null for a fresh create and set to the
  // preset id when editing an existing row (drives POST vs PUT).
  const [editingId, setEditingId] = React.useState<string | null>(null);
  const [name, setName] = React.useState("");
  const [description, setDescription] = React.useState("");
  // Config captured from <PresetConfigForm/> onChange. `seedConfig` is the
  // config passed to the form as `initialConfig` on mount (set when entering
  // author mode so the form seeds from the right preset / a blank realtime
  // default). The form owns its own state and only reports built config up.
  const [seedConfig, setSeedConfig] = React.useState<
    Record<string, unknown> | null
  >(null);
  const [config, setConfig] = React.useState<Record<string, unknown> | null>(
    null,
  );
  const [configValid, setConfigValid] = React.useState(true);
  const [inlineError, setInlineError] = React.useState<string | null>(null);
  // The preset pending a type-to-confirm delete (null while the dialog closed).
  const [deleteTarget, setDeleteTarget] = React.useState<Preset | null>(null);

  const createMutation = useCreatePreset();
  const updateMutation = useUpdatePreset();
  const publishMutation = usePublishPreset();
  // Platform-admin-only surface: list drafts + published for the manage view.
  const { data: presets = [] } = usePresets({ includeDrafts: true });

  // Clear every author-form field so the admin can author another preset after
  // a successful save (an inline panel has no dialog to close, so it resets).
  const resetForm = React.useCallback(() => {
    setEditingId(null);
    setName("");
    setDescription("");
    setSeedConfig(null);
    setConfig(null);
    setConfigValid(true);
    setInlineError(null);
  }, []);

  /** Enter author mode for a brand-new preset (blank realtime default). */
  const startCreate = React.useCallback(() => {
    resetForm();
    setView("author");
  }, [resetForm]);

  /** Enter author mode seeded from an existing preset (edit → PUT). */
  const startEdit = React.useCallback((preset: Preset) => {
    setEditingId(preset.id);
    setName(preset.name);
    setDescription(preset.description ?? "");
    setSeedConfig(preset.config);
    setConfig(preset.config);
    setConfigValid(true);
    setInlineError(null);
    setView("author");
  }, []);

  const handleSave = async (isPublished: boolean) => {
    setInlineError(null);
    if (!name.trim()) {
      setInlineError("Name is required.");
      return;
    }
    if (!configValid || !config) {
      setInlineError("Fix the invalid params JSON before saving.");
      return;
    }
    try {
      if (editingId) {
        await updateMutation.mutateAsync({
          presetId: editingId,
          payload: {
            name: name.trim(),
            description: description.trim() || null,
            config,
            is_published: isPublished,
          },
        });
      } else {
        await createMutation.mutateAsync({
          name: name.trim(),
          description: description.trim() || null,
          config,
          is_published: isPublished,
        });
      }
      // Inline panel has no dialog to close — reset the form so the admin can
      // author another preset. The create/update hooks invalidate the preset
      // list, so the manage view refetches with the new/edited row.
      resetForm();
      setView("manage");
    } catch (e) {
      // Backend 400 (invalid SpeechConfig) detail surfaces here.
      setInlineError(
        e instanceof Error ? e.message : "Failed to save preset.",
      );
    }
  };

  const handlePublishToggle = (preset: Preset) => {
    publishMutation.mutate({
      presetId: preset.id,
      published: !preset.is_published,
    });
  };

  // Preset delete opens the type-to-confirm dialog. The dialog pre-fetches
  // usage and sends `force = count > 0` after explicit confirmation.
  const handleDelete = (preset: Preset) => {
    setDeleteTarget(preset);
  };

  const isBusy =
    createMutation.isPending ||
    updateMutation.isPending ||
    publishMutation.isPending;

  const canSubmit = name.trim().length > 0 && configValid;

  return (
    <div className="space-y-6">
      {/* View toggle (plain state — inline panel). Manage is first and the
          default — the page lands the admin on the preset list; authoring a
          new preset is opt-in via the second toggle. */}
      <div className="inline-flex items-center rounded-lg border bg-muted/40 p-1">
        <button
          type="button"
          className={cn(
            "px-3 py-1.5 text-sm rounded-md transition-colors",
            view === "manage"
              ? "bg-background shadow-sm font-medium"
              : "text-muted-foreground hover:text-foreground",
          )}
          onClick={() => setView("manage")}
        >
          Manage existing presets ({presets.length})
        </button>
        <button
          type="button"
          className={cn(
            "px-3 py-1.5 text-sm rounded-md transition-colors",
            view === "author"
              ? "bg-background shadow-sm font-medium"
              : "text-muted-foreground hover:text-foreground",
          )}
          onClick={startCreate}
        >
          {editingId && view === "author" ? "Editing preset" : "Author preset"}
        </button>
      </div>

      {view === "author" ? (
        <div className="space-y-5">
          {editingId && (
            <p className="text-xs text-muted-foreground">
              Editing <span className="font-medium">{name}</span>. Save draft or
              publish to apply changes (takes effect on each agent&apos;s next
              call).
            </p>
          )}
          <div className="space-y-3">
            <div className="space-y-1">
              <Label
                htmlFor="preset-name"
                className="text-xs uppercase text-muted-foreground"
              >
                Name <span className="text-destructive">*</span>
              </Label>
              <Input
                id="preset-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Realtime (Gemini) default"
                className="h-9 text-sm"
              />
            </div>
            <div className="space-y-1">
              <Label
                htmlFor="preset-description"
                className="text-xs uppercase text-muted-foreground"
              >
                Description (optional — shown to org admins in the picker)
              </Label>
              <Input
                id="preset-description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="What this voice profile is for"
                className="h-9 text-sm"
              />
            </div>
          </div>

          {/* The SpeechConfig authoring sub-form. `key` forces a fresh mount
              whenever the seed changes (new preset vs editing a different row)
              so the form's internal state re-seeds from `initialConfig`. */}
          <PresetConfigForm
            key={editingId ?? "new"}
            initialConfig={seedConfig}
            onChange={setConfig}
            onValidityChange={setConfigValid}
          />

          {inlineError && (
            <div className="flex items-start gap-2 p-3 rounded-lg border bg-red-50 dark:bg-red-950/20 border-red-200 dark:border-red-800">
              <div className="text-xs text-red-700 dark:text-red-300">
                {inlineError}
              </div>
            </div>
          )}

          {/* Inline footer. Buttons are w-full on mobile, auto-width side-by-side
              at sm+ so they never overflow the panel. */}
          <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
            <Button
              onClick={() => handleSave(false)}
              disabled={!canSubmit || isBusy}
              variant="outline"
              className="w-full sm:w-auto"
            >
              {createMutation.isPending || updateMutation.isPending ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Plus className="h-4 w-4 mr-2" />
              )}
              Save draft
            </Button>
            <Button
              onClick={() => handleSave(true)}
              disabled={!canSubmit || isBusy}
              className="w-full sm:w-auto"
            >
              {createMutation.isPending || updateMutation.isPending ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Upload className="h-4 w-4 mr-2" />
              )}
              Publish
            </Button>
          </div>
        </div>
      ) : (
        // Manage view: drafts + published, with publish/unpublish/edit/delete.
        <div className="space-y-3">
          <p className="text-xs text-muted-foreground">
            Drafts are visible only to platform admins. Publishing surfaces a
            preset in every org&apos;s agent picker; unpublishing hides it from
            new assignments (existing assignments keep working until cleared).
          </p>
          {presets.length === 0 ? (
            <div className="text-center py-8 bg-muted/20 rounded-lg border border-dashed">
              <SlidersHorizontal className="h-8 w-8 text-muted-foreground mx-auto mb-2 opacity-50" />
              <p className="text-sm text-muted-foreground">
                No voice presets yet. Author a preset to get started.
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              {presets.map((preset) => (
                <div
                  key={preset.id}
                  className="flex items-center justify-between gap-3 p-3 rounded-lg border bg-muted/20"
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-0.5">
                      <span className="text-sm font-medium">{preset.name}</span>
                      <Badge variant="secondary" className="h-5 text-[10px]">
                        {preset.preset_type === "realtime"
                          ? "Realtime"
                          : "Pipeline"}
                      </Badge>
                      <Badge
                        variant={preset.is_published ? "default" : "outline"}
                        className="h-5 text-[10px]"
                      >
                        {preset.is_published ? "Published" : "Draft"}
                      </Badge>
                    </div>
                    {preset.description && (
                      <p className="text-xs text-muted-foreground line-clamp-2">
                        {preset.description}
                      </p>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handlePublishToggle(preset)}
                      disabled={isBusy}
                    >
                      {preset.is_published ? "Unpublish" : (
                        <>
                          <Upload className="h-3.5 w-3.5 mr-1" />
                          Publish
                        </>
                      )}
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => startEdit(preset)}
                      disabled={isBusy}
                      aria-label="Edit"
                    >
                      <Pencil className="h-3.5 w-3.5" />
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => handleDelete(preset)}
                      disabled={isBusy}
                      aria-label="Delete"
                    >
                      <Trash2 className="h-3.5 w-3.5 text-destructive" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Conditionally rendered so the shared DeleteConfirmationDialog mounts
          fresh each open — its internal type-to-confirm state resets between
          deletes (always-mounted would leak "Delete" into the next dialog). */}
      {deleteTarget && (
        <PresetDeleteDialog
          open
          onOpenChange={(o) => {
            if (!o) setDeleteTarget(null);
          }}
          preset={deleteTarget}
          onDeleted={() => setDeleteTarget(null)}
        />
      )}
    </div>
  );
}