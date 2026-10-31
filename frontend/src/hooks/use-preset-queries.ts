import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { presetService } from "@/services/preset-service";
import type { PresetCreate, PresetUpdate, PresetType } from "@/types/preset";
import { toast } from "sonner";

/**
 * React-Query hooks for the platform-admin voice-engine preset catalog
 * (`/api/v1/presets`). Mirrors the platform-tools hooks in
 * `use-agent-queries.ts`.
 *
 * Query keys are namespaced under `["presets"]`; the `includeDrafts` flag is
 * part of the list key so flipping it refetches.
 */
export const presetQueryKeys = {
  all: ["presets"] as const,
  list: (opts?: { presetType?: PresetType; includeDrafts?: boolean }) =>
    [
      ...presetQueryKeys.all,
      {
        type: opts?.presetType ?? null,
        drafts: opts?.includeDrafts ?? false,
      },
    ] as const,
  detail: (id: string) => [...presetQueryKeys.all, id] as const,
  usage: (id: string) => [...presetQueryKeys.all, id, "usage"] as const,
  default: () => [...presetQueryKeys.all, "default"] as const,
  catalog: (opts: { organizationId: string; usePlatformCredits?: boolean }) =>
    [
      ...presetQueryKeys.all,
      "catalog",
      {
        org: opts.organizationId,
        credits: opts.usePlatformCredits ?? false,
      },
    ] as const,
};

/**
 * List presets visible to the caller. Org users see only published rows (the
 * agent picker catalog); platform admins pass `{ includeDrafts: true }` to also
 * see drafts. `presetType` filters by `realtime` | `pipeline`.
 */
export function usePresets(opts?: {
  presetType?: PresetType;
  includeDrafts?: boolean;
}) {
  return useQuery({
    queryKey: presetQueryKeys.list(opts),
    queryFn: () => presetService.listPresets(opts),
    staleTime: 5 * 60 * 1000, // 5 minutes — presets change rarely
  });
}

/**
 * Org-facing white-label voice profile catalog with per-org readiness flags.
 *
 * Used by `PresetPicker` on agent create/detail. Requires `organizationId`;
 * pass `usePlatformCredits` when mirroring the agent's billing toggle.
 */
export function usePresetCatalog(opts: {
  organizationId: string | null | undefined;
  usePlatformCredits?: boolean;
}) {
  const orgId = opts.organizationId ?? "";
  return useQuery({
    queryKey: presetQueryKeys.catalog({
      organizationId: orgId,
      usePlatformCredits: opts.usePlatformCredits,
    }),
    queryFn: () =>
      presetService.getPresetCatalog({
        organizationId: orgId,
        usePlatformCredits: opts.usePlatformCredits,
      }),
    enabled: !!orgId,
    staleTime: 60 * 1000,
  });
}

/** Fetch a single preset by id (drafts are platform-admin-only on the backend). */
export function usePreset(presetId: string, enabled = true) {
  return useQuery({
    queryKey: presetQueryKeys.detail(presetId),
    queryFn: () => presetService.getPreset(presetId),
    enabled: !!presetId && enabled,
    staleTime: 30 * 1000,
  });
}

/**
 * Fetch the current platform default preset (platform-admin only). It is
 * published and appears as the dynamic null-selection option in org pickers.
 * The manage view already receives it via `usePresets({ includeDrafts: true })`;
 * this hook remains for the legacy default editor/API.
 */
export function useDefaultPreset() {
  return useQuery({
    queryKey: presetQueryKeys.default(),
    queryFn: () => presetService.getDefaultPreset(),
    staleTime: 30 * 1000,
  });
}

// Mutation: Create a preset (upsert by name). Invalidates the preset list so the
// new row appears immediately. The manager surfaces backend validation detail
// inline via the thrown error message.
export function useCreatePreset() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: PresetCreate) => presetService.createPreset(payload),
    onSuccess: () => {
      toast.success("Preset saved");
      queryClient.invalidateQueries({ queryKey: presetQueryKeys.all });
    },
    onError: () => {
      toast.error("Failed to save preset");
    },
  });
}

// Mutation: Update a preset (re-validates config server-side). Invalidates the
// list so edits surface immediately.
export function useUpdatePreset() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      presetId,
      payload,
    }: {
      presetId: string;
      payload: PresetUpdate;
    }) => presetService.updatePreset(presetId, payload),
    onSuccess: () => {
      toast.success("Preset updated");
      queryClient.invalidateQueries({ queryKey: presetQueryKeys.all });
    },
    onError: () => {
      toast.error("Failed to update preset");
    },
  });
}

// Mutation: Replace the platform default's `config` through the legacy API.
// The backend keeps it published and platform-managed; invalidate the preset
// list and default row so both admin and org picker views refresh.
export function useUpdateDefaultPreset() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (config: Record<string, unknown>) =>
      presetService.updateDefaultPreset(config),
    onSuccess: () => {
      toast.success("Platform default updated");
      queryClient.invalidateQueries({ queryKey: presetQueryKeys.all });
    },
    onError: () => {
      toast.error("Failed to update platform default");
    },
  });
}

// Mutation: Publish / unpublish a preset (platform-admin only). Invalidates the
// preset list so the row's publish state refreshes immediately.
export function usePublishPreset() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      presetId,
      published,
    }: {
      presetId: string;
      published: boolean;
    }) => presetService.publishPreset(presetId, published),
    onSuccess: (_data, { published }) => {
      toast.success(published ? "Preset published" : "Preset unpublished");
      queryClient.invalidateQueries({ queryKey: presetQueryKeys.all });
    },
    onError: (error) => {
      toast.error(
        error instanceof Error
          ? error.message
          : "Failed to update publish state",
      );
    },
  });
}

/** Select a published platform-managed voice profile as the global default. */
export function useSetDefaultPreset() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (presetId: string) => presetService.setDefaultPreset(presetId),
    onSuccess: () => {
      toast.success("Platform default updated");
      queryClient.invalidateQueries({ queryKey: presetQueryKeys.all });
    },
    onError: (error) => {
      toast.error(
        error instanceof Error
          ? error.message
          : "Failed to update platform default",
      );
    },
  });
}

// Mutation: Delete a preset (platform-admin only). `force` is required to delete
// a preset referenced by agents (backend 409 `in_use` otherwise). The
// delete-confirm dialog pre-fetches usage via `usePresetUsage` and passes
// `force = count > 0` after a type-to-confirm, so the 409 path is a backend
// safety net. A force-delete sets `voice_agents.preset_id` to NULL via the FK,
// so every agent query is invalidated to drop the stale preset reference.
export function useDeletePreset() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      presetId,
      force = false,
    }: {
      presetId: string;
      force?: boolean;
    }) => presetService.deletePreset(presetId, force),
    onSuccess: () => {
      toast.success("Preset deleted");
      queryClient.invalidateQueries({ queryKey: presetQueryKeys.all });
      // A force-delete detaches the preset from every using agent (preset_id ->
      // NULL via the FK), so agent detail/list queries must refetch.
      queryClient.invalidateQueries({ queryKey: ["agents"] });
    },
    onError: () => {
      toast.error("Failed to delete preset");
    },
  });
}

// Query: agents currently using a preset (platform-admin only). Powers the
// delete-confirm dialog's "used by N agents" warning list. `enabled` lets the
// caller gate the fetch (e.g. only when the delete dialog opens).
export function usePresetUsage(presetId: string, enabled = true) {
  return useQuery({
    queryKey: presetQueryKeys.usage(presetId),
    queryFn: () => presetService.getPresetUsage(presetId),
    enabled: !!presetId && enabled,
    staleTime: 0, // always refetch when the dialog opens — usage can change fast
  });
}
