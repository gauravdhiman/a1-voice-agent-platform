"use client";

import * as React from "react";
import { Loader2, CheckCircle2, SlidersHorizontal } from "lucide-react";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { usePresetCatalog } from "@/hooks/use-preset-queries";
import { DEFAULT_PRESET_DISPLAY } from "@/types/preset";
import { PresetSetupCallout } from "@/components/agents/preset-setup-callout";

/**
 * PresetPicker — reusable single-select "Voice profile" picker (white-label).
 *
 * Org admins see published voice profiles by **name + description + readiness
 * status** only. Engine mode, pipeline stages, and provider names are never
 * shown. Readiness (`Ready` / `Setup required`) is computed server-side per org.
 *
 * The `preset_id = null` option uses `DEFAULT_PRESET_DISPLAY` (matches the
 * platform-admin "System Default" row label) with no engine badge.
 *
 * When a not-ready profile is selected, a generic setup callout appears (no
 * provider names). Org admins with self-service credentials get a link to
 * Organization → API Credentials; managed orgs are told to contact platform admin.
 *
 * @example
 * ```tsx
 * <PresetPicker
 *   organizationId={agent.organization_id}
 *   usePlatformCredits={agentForm.use_platform_credits}
 *   value={agentForm.preset_id}
 *   onChange={(id) => setAgentForm({ ...agentForm, preset_id: id })}
 * />
 * ```
 */
export interface PresetPickerProps {
  /** Owning organization — required for org-scoped readiness from the catalog API. */
  organizationId: string;
  /** Mirrors the agent's "Use plan credits" toggle when evaluating readiness. */
  usePlatformCredits?: boolean;
  /** Currently selected preset id, or `null` for the system default. */
  value: string | null;
  /** Fired with the new preset id (or `null` when the default is chosen). */
  onChange: (presetId: string | null) => void;
  className?: string;
  disabled?: boolean;
}

export function PresetPicker({
  organizationId,
  usePlatformCredits = false,
  value,
  onChange,
  className,
  disabled = false,
}: PresetPickerProps) {
  const { data: catalog, isLoading } = usePresetCatalog({
    organizationId,
    usePlatformCredits,
  });

  const presets = catalog?.presets ?? [];
  const defaultIsReady = catalog?.default_is_ready ?? true;
  const credentialsSelfService = catalog?.credentials_self_service ?? true;

  const selectedIsReady = React.useMemo(() => {
    if (value === null) return defaultIsReady;
    return presets.find((p) => p.id === value)?.is_ready ?? true;
  }, [value, defaultIsReady, presets]);

  const showSetupCallout = !selectedIsReady && !isLoading;

  return (
    <div className={cn("space-y-2", className)}>
      <div className="space-y-1">
        <p className="text-sm font-medium">Voice profile</p>
        <p className="text-xs text-muted-foreground">
          Pick a published voice profile for this agent, or use the system
          default. Profiles marked Ready are fully configured for your
          organization.
        </p>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-4">
          <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
        </div>
      ) : (
        <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
          <PresetOption
            selected={value === null}
            onSelect={() => onChange(null)}
            name={DEFAULT_PRESET_DISPLAY.name}
            description={DEFAULT_PRESET_DISPLAY.description}
            isReady={defaultIsReady}
            disabled={disabled}
          />
          {presets.length === 0 ? (
            <div className="text-center py-4 bg-muted/20 rounded-lg border border-dashed">
              <SlidersHorizontal className="h-6 w-6 text-muted-foreground mx-auto mb-1 opacity-50" />
              <p className="text-xs text-muted-foreground">
                No voice profiles published yet — this agent will use the system
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
                isReady={preset.is_ready}
                disabled={disabled}
              />
            ))
          )}
        </div>
      )}

      {showSetupCallout && (
        <PresetSetupCallout
          credentialsSelfService={credentialsSelfService}
          organizationId={organizationId}
        />
      )}
    </div>
  );
}

/** Exported helper: is the current selection ready (for agent-level banners). */
export function useSelectedPresetReadiness(
  organizationId: string | null | undefined,
  presetId: string | null,
  usePlatformCredits = false,
): { isReady: boolean; isLoading: boolean; credentialsSelfService: boolean } {
  const { data: catalog, isLoading } = usePresetCatalog({
    organizationId,
    usePlatformCredits,
  });

  if (isLoading || !catalog) {
    return {
      isReady: true,
      isLoading,
      credentialsSelfService: true,
    };
  }

  const isReady =
    presetId === null
      ? catalog.default_is_ready
      : (catalog.presets.find((p) => p.id === presetId)?.is_ready ?? true);

  return {
    isReady,
    isLoading,
    credentialsSelfService: catalog.credentials_self_service,
  };
}

/** A single selectable row in the picker (default option or a catalog item). */
function PresetOption({
  selected,
  onSelect,
  name,
  description,
  isReady,
  disabled = false,
}: {
  selected: boolean;
  onSelect: () => void;
  name: string;
  description?: string;
  isReady: boolean;
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
        <Badge
          variant={isReady ? "secondary" : "outline"}
          className={cn(
            "text-[10px] h-5",
            isReady
              ? "text-green-700 border-green-200 bg-green-50 dark:text-green-300 dark:border-green-900 dark:bg-green-950/40"
              : "text-amber-700 border-amber-200 bg-amber-50 dark:text-amber-300 dark:border-amber-900 dark:bg-amber-950/40",
          )}
        >
          {isReady ? "Ready" : "Setup required"}
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
