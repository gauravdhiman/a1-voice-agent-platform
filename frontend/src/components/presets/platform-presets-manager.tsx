"use client";

import * as React from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Loader2,
  Plus,
  SlidersHorizontal,
  Upload,
  Pencil,
  Trash2,
} from "lucide-react";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import type { Preset } from "@/types/preset";
import { DEFAULT_PRESET_DISPLAY } from "@/types/preset";
import {
  usePresets,
  useCreatePreset,
  useUpdatePreset,
  usePublishPreset,
  useUpdateDefaultPreset,
} from "@/hooks/use-preset-queries";
import { PresetConfigForm } from "@/components/presets/preset-config-form";
import { PresetDeleteDialog } from "@/components/presets/preset-delete-dialog";

/**
 * PlatformPresetsManager — platform-admin surface for the voice-engine
 * preset catalog (`/platform/presets`). Mirrors
 * `platform-tools-manager.tsx`: a manage catalog with a right-side create/edit
 * drawer, plain `.map()` row-cards with `Badge` Published/Draft + type badge +
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
 * The manage catalog stays on the page while create/edit opens in the shared
 * right-side Sheet pattern:
 *  - **Create / edit preset** (`view === "author"`): name + description +
 *    `<PresetConfigForm/>` + "Save draft" / "Publish". In edit mode
 *    (`editingId` set) the form is seeded from the selected preset and submit
 *    issues `PUT /{id}`; otherwise `POST /` (upsert by name). On success the
 *    form resets and the manage list refetches.
 *  - **Manage existing presets** (`view === "manage"`): lists drafts +
 *    published presets with publish/unpublish, edit, and delete actions.
 *
 * Conventions match `platform-tools-manager.tsx`: plain useState, no
 * react-hook-form, no window.* dialogs, and a right-side drawer for create/edit.
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
  // preset id when editing an existing row (drives POST vs PUT). `editingDefault`
  // is true when editing the system-default row — that path saves via
  // `useUpdateDefaultPreset` (config only; name/is_published stay fixed) and
  // never goes through the normal create/update mutations.
  const [editingId, setEditingId] = React.useState<string | null>(null);
  const [editingDefault, setEditingDefault] = React.useState(false);
  const [name, setName] = React.useState("");
  const [description, setDescription] = React.useState("");
  // Config captured from <PresetConfigForm/> onChange. `seedConfig` is the
  // config passed to the form as `initialConfig` on mount (set when entering
  // author mode so the form seeds from the right preset / a blank realtime
  // default). The form owns its own state and only reports built config up.
  const [seedConfig, setSeedConfig] = React.useState<Record<
    string,
    unknown
  > | null>(null);
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
  const updateDefaultMutation = useUpdateDefaultPreset();
  // Platform-admin-only surface: list drafts + published for the manage view.
  const { data: presets = [] } = usePresets({ includeDrafts: true });

  // Clear every author-form field when starting a fresh preset or after a
  // successful save before returning to the catalog.
  const resetForm = React.useCallback(() => {
    setEditingId(null);
    setEditingDefault(false);
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
    setEditingDefault(false);
    setName(preset.name);
    setDescription(preset.description ?? "");
    setSeedConfig(preset.config);
    setConfig(preset.config);
    setConfigValid(true);
    setInlineError(null);
    setView("author");
  }, []);

  /**
   * Enter author mode seeded from the system default preset. The default is
   * edited via `useUpdateDefaultPreset` (config only); its name is fixed
   * ("System Default") and it is never publishable/deletable, so the author
   * form is read-only on name/description and shows a single "Save config"
   * button instead of Save draft / Publish.
   */
  const startEditDefault = React.useCallback((preset: Preset) => {
    setEditingId(preset.id);
    setEditingDefault(true);
    setName(preset.name);
    setDescription(preset.description ?? "");
    setSeedConfig(preset.config);
    setConfig(preset.config);
    setConfigValid(true);
    setInlineError(null);
    setView("author");
  }, []);

  /**
   * Save the system default's `config` (config-only write; name/is_published/
   * is_default stay fixed on the backend). Distinct from `handleSave` so the
   * default never goes through the create/update/publish paths.
   */
  const handleSaveDefault = async () => {
    setInlineError(null);
    if (!configValid || !config) {
      setInlineError("Fix the invalid params JSON before saving.");
      return;
    }
    try {
      await updateDefaultMutation.mutateAsync(config);
      resetForm();
      setView("manage");
    } catch (e) {
      // Backend 400 (invalid SpeechConfig) or 404 (no default row) detail.
      setInlineError(
        e instanceof Error ? e.message : "Failed to update system default.",
      );
    }
  };

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
      // Close the authoring drawer after save. The create/update hooks
      // invalidate the preset list, so the manage view refetches with the
      // new/edited row.
      resetForm();
      setView("manage");
    } catch (e) {
      // Backend 400 (invalid SpeechConfig) detail surfaces here.
      setInlineError(e instanceof Error ? e.message : "Failed to save preset.");
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
    publishMutation.isPending ||
    updateDefaultMutation.isPending;

  const canSubmit = name.trim().length > 0 && configValid;

  // Manage list: pin the system-default row to the top (it is the fallback
  // every agent with no preset uses); keep the API order for the rest. Stable
  // sort so the default is first without shuffling authored presets.
  const sortedPresets = React.useMemo(
    () =>
      [...presets].sort((a, b) =>
        a.is_default === b.is_default ? 0 : a.is_default ? -1 : 1,
      ),
    [presets],
  );

  return (
    <div className="space-y-6">
      {view === "author" ? (
        <Sheet
          open
          onOpenChange={(open) => {
            if (!open) {
              resetForm();
              setView("manage");
            }
          }}
        >
          <SheetContent className="form-drawer flex w-full flex-col overflow-hidden sm:max-w-2xl">
            <SheetHeader className="shrink-0 border-b px-6 pb-5 pt-6">
              <SheetTitle>
                {editingDefault
                  ? "Edit system default"
                  : editingId
                    ? "Edit voice preset"
                    : "Create voice preset"}
              </SheetTitle>
              <SheetDescription>
                {editingDefault
                  ? "Update the fallback voice profile used when an agent has no profile selected."
                  : editingId
                    ? "Update this voice profile without leaving the preset catalog."
                    : "Create a reusable voice profile for Org Admins to select on their agents."}
              </SheetDescription>
            </SheetHeader>
            <div className="min-h-0 flex-1 overflow-y-auto px-6 py-5">
              <div className="form-surface space-y-5">
                {editingDefault ? (
                  <p className="text-xs text-muted-foreground">
                    Editing the{" "}
                    <span className="font-medium">System Default</span> — the
                    fallback voice profile used when an agent has no voice
                    profile selected. Only the config is editable; the name
                    stays fixed and the default is never publishable or
                    deletable. Changes take effect on each agent&apos;s next
                    call.
                  </p>
                ) : editingId ? (
                  <p className="text-xs text-muted-foreground">
                    Editing <span className="font-medium">{name}</span>. Save
                    draft or publish to apply changes (takes effect on each
                    agent&apos;s next call).
                  </p>
                ) : null}
                <div className="form-section space-y-3">
                  <div className="form-field space-y-1">
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
                      className="form-control h-9 text-sm"
                      disabled={editingDefault}
                      readOnly={editingDefault}
                    />
                  </div>
                  {!editingDefault && (
                    <div className="form-field space-y-1">
                      <Label
                        htmlFor="preset-description"
                        className="text-xs uppercase text-muted-foreground"
                      >
                        Description (optional — shown to org admins in the
                        picker)
                      </Label>
                      <Input
                        id="preset-description"
                        value={description}
                        onChange={(e) => setDescription(e.target.value)}
                        placeholder="What this voice profile is for"
                        className="form-control h-9 text-sm"
                      />
                    </div>
                  )}
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

                {editingDefault ? (
                  // Default: config-only write via useUpdateDefaultPreset. No
                  // Save-draft/Publish — the default is never publishable.
                  <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
                    <Button
                      onClick={handleSaveDefault}
                      disabled={!configValid || !config || isBusy}
                      className="w-full sm:w-auto"
                    >
                      {updateDefaultMutation.isPending ? (
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      ) : (
                        <SlidersHorizontal className="h-4 w-4 mr-2" />
                      )}
                      Save config
                    </Button>
                  </div>
                ) : (
                  // Drawer footer. Buttons are w-full on mobile, auto-width
                  // side-by-side at sm+ so they never overflow the panel.
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
                )}
              </div>
            </div>
          </SheetContent>
        </Sheet>
      ) : (
        // Manage view: drafts + published, with publish/unpublish/edit/delete.
        <div className="space-y-3">
          <div className="flex flex-col gap-3 rounded-2xl border bg-muted/20 p-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="text-sm font-semibold">Voice preset catalog</h2>
              <p className="mt-1 text-xs text-muted-foreground">
                Create reusable voice profiles or manage the presets already
                available to Org Admins.
              </p>
            </div>
            <Button onClick={startCreate} className="w-full sm:w-auto">
              <Plus className="mr-2 h-4 w-4" />
              Create new preset
            </Button>
          </div>
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
              {sortedPresets.map((preset) =>
                preset.is_default ? (
                  // The system-default row — the fallback every agent with no
                  // preset uses. Immutable except its config: not publishable,
                  // not deletable, name fixed. Only "Edit config" is exposed,
                  // which seeds the author form and saves via the default path.
                  <div
                    key={preset.id}
                    className="flex items-center justify-between gap-3 p-3 rounded-lg border border-primary/30 bg-primary/5"
                  >
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-0.5">
                        <span className="text-sm font-medium">
                          {DEFAULT_PRESET_DISPLAY.name}
                        </span>
                        <Badge variant="default" className="h-5 text-[10px]">
                          Default
                        </Badge>
                        <Badge variant="secondary" className="h-5 text-[10px]">
                          {preset.preset_type === "realtime"
                            ? "Realtime"
                            : "Pipeline"}
                        </Badge>
                      </div>
                      <p className="text-xs text-muted-foreground line-clamp-2">
                        {DEFAULT_PRESET_DISPLAY.description}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => startEditDefault(preset)}
                        disabled={isBusy}
                      >
                        <Pencil className="h-3.5 w-3.5 mr-1" />
                        Edit config
                      </Button>
                    </div>
                  </div>
                ) : (
                  <div
                    key={preset.id}
                    className="flex items-center justify-between gap-3 p-3 rounded-lg border bg-muted/20"
                  >
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-0.5">
                        <span className="text-sm font-medium">
                          {preset.name}
                        </span>
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
                        {preset.is_published ? (
                          "Unpublish"
                        ) : (
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
                ),
              )}
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
