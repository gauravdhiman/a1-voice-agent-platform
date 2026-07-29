"use client";

import * as React from "react";
import { Loader2, CheckCircle2, SlidersHorizontal } from "lucide-react";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { usePresets } from "@/hooks/use-preset-queries";
import type { Preset } from "@/types/preset";

/**
 * PresetPicker — reusable single-select "Voice profile" picker.
 *
 * Used by both the agent create widget and the agent detail Properties tab. The
 * org admin picks one published preset (a "voice profile") for the agent, or
 * "Default (Gemini Realtime)" to clear the assignment (`preset_id = null`).
 *
 * Locked UX decision: the end user NEVER sees `engine_mode` / STT / LLM / TTS
 * here — only preset name + description + a **subtle** type badge
 * ("Realtime"/"Pipeline"). The engine + stage detail is a platform-admin
 * concern, authored on `/platform/presets`.
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
  /** Currently selected preset id, or `null` for the realtime default. */
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
          Pick a published voice profile for this agent, or use the default
          (Google Gemini realtime). Only the name + description are shown — the
          engine + stage configuration is managed by platform admins.
        </p>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-4">
          <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
        </div>
      ) : (
        <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
          {/* Default option -> preset_id = null (realtime default). */}
          <PresetOption
            selected={value === null}
            onSelect={() => onChange(null)}
            name="Default (Gemini Realtime)"
            description="End-to-end Google Gemini native-audio model."
            typeBadge="Realtime"
            disabled={disabled}
          />
          {presets.length === 0 ? (
            <div className="text-center py-4 bg-muted/20 rounded-lg border border-dashed">
              <SlidersHorizontal className="h-6 w-6 text-muted-foreground mx-auto mb-1 opacity-50" />
              <p className="text-xs text-muted-foreground">
                No voice profiles published yet — this agent will use the
                default.
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
  typeBadge: "Realtime" | "Pipeline";
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
        <Badge variant="secondary" className="text-[10px] h-5">
          {typeBadge}
        </Badge>
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