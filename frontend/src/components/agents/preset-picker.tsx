"use client";

import * as React from "react";
import { Loader2, CheckCircle2, SlidersHorizontal } from "lucide-react";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { usePresets } from "@/hooks/use-preset-queries";
import { DEFAULT_PRESET_DISPLAY } from "@/types/preset";
import type { Preset } from "@/types/preset";

/**
 * PresetPicker — reusable single-select "Voice profile" picker.
 *
 * Used by both the agent create widget and the agent detail Properties tab. The
 * org admin picks one published preset (a "voice profile") for the agent, or
 * the system-default fallback to clear the assignment (`preset_id = null`).
 *
 * The `preset_id = null` option is labeled with `DEFAULT_PRESET_DISPLAY` — the
 * SAME name + description the platform admin sees for the "System Default" row
 * on `/platform/presets` — so the two surfaces can't drift. It deliberately
 * shows NO type badge: the system default's underlying engine is a
 * platform-admin concern (the admin sets it on `/platform/presets`), so the
 * picker must not leak it. "System Default" is the backend reserved name, so it
 * can never collide with a published preset name in this list.
 *
 * Controlled: `value` is the current `preset_id` (or `null`); `onChange` fires
 * with the new `preset_id` (preset id or `null` for the default). Lists only
 * **published** presets (`usePresets()` with no `includeDrafts`) — the agent
 * picker catalog is the published surface; drafts are platform-admin-only.
 *
 * @example
 * ```tsx
 * <PresetPicker value={agentForm.preset_id} onChange={(id) => setAgentForm({ ...agentForm, preset_id: id })} />
 * ```
 */
export interface PresetPickerProps {
  /** Currently selected preset id, or `null` for the system default. */
  value: string | null;
  /** Fired with the new preset id (or `null` when the default is chosen). */
  onChange: (presetId: string | null) => void;
  /** Optional extra className for the wrapper. */
  className?: string;
  /** When true, the options render read-only (no selection). */
  disabled?: boolean;
}

export function PresetPicker({
  value,
  onChange,
  className,
  disabled = false,
}: PresetPickerProps) {
  // Published-only — drafts are not selectable by org users. The backend
  // independently rejects a draft preset_id on agent create/update.
  const { data: presets = [], isLoading } = usePresets();

  return (
    <div className={cn("space-y-2", className)}>
      <div className="space-y-1">
        <p className="text-sm font-medium">Voice profile</p>
        <p className="text-xs text-muted-foreground">
          Pick a published voice profile for this agent, or use the system
          default. Only the name + description are shown — the engine + stage
          configuration is managed by platform admins.
        </p>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-4">
          <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
        </div>
      ) : (
        <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
          {/* System-default fallback -> preset_id = null. Labeled with
              DEFAULT_PRESET_DISPLAY so it matches the platform-admin Voice
              Presets page exactly. No type badge: the default's underlying
              engine is a platform-admin concern (set on /platform/presets), so
              the picker does not leak it. "System Default" is the backend
              reserved name, so it can't collide with a published preset. */}
          <PresetOption
            selected={value === null}
            onSelect={() => onChange(null)}
            name={DEFAULT_PRESET_DISPLAY.name}
            description={DEFAULT_PRESET_DISPLAY.description}
            disabled={disabled}
          />
          {presets.length === 0 ? (
            <div className="text-center py-4 bg-muted/20 rounded-lg border border-dashed">
              <SlidersHorizontal className="h-6 w-6 text-muted-foreground mx-auto mb-1 opacity-50" />
              <p className="text-xs text-muted-foreground">
                No voice profiles published yet — this agent will use the
                system default.
              </p>
            </div>
          ) : (
            presets.map((preset) => (
              <PresetOption
                key={preset.id}
                selected={value === preset.id}
                onSelect={() => onChange(preset.id)}
                name={preset.name}
                description={preset.description ?? undefined}
                typeBadge={preset.preset_type === "realtime" ? "Realtime" : "Pipeline"}
                disabled={disabled}
              />
            ))
          )}
        </div>
      )}
    </div>
  );
}

/** A single selectable row in the picker (default option or a preset). */
function PresetOption({
  selected,
  onSelect,
  name,
  description,
  typeBadge,
  disabled = false,
}: {
  selected: boolean;
  onSelect: () => void;
  name: string;
  description?: string;
  /** Optional engine badge. Omitted for the system-default fallback option so
   * the picker does not leak the system default's underlying engine. */
  typeBadge?: "Realtime" | "Pipeline";
  disabled?: boolean;
}) {
  return (
    <div
      role="radio"
      aria-checked={selected}
      aria-disabled={disabled}
      tabIndex={disabled ? -1 : 0}
      onClick={disabled ? undefined : onSelect}
      onKeyDown={
        disabled
          ? undefined
          : (e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                onSelect();
              }
            }
      }
      className={cn(
        "p-3 border-2 rounded-lg transition-all",
        disabled
          ? "cursor-not-allowed opacity-70"
          : "cursor-pointer hover:border-primary/40 hover:bg-muted/40",
        selected ? "border-primary bg-primary/5" : "border-border",
      )}
    >
      <div className="flex items-center gap-2 flex-wrap">
        <span className="font-medium text-sm text-foreground">{name}</span>
        {typeBadge && (
          <Badge variant="secondary" className="text-[10px] h-5">
            {typeBadge}
          </Badge>
        )}
        {selected && <CheckCircle2 className="h-4 w-4 text-primary" />}
      </div>
      {description && (
        <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">
          {description}
        </p>
      )}
    </div>
  );
}