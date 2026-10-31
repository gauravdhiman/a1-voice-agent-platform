// services/preset-service.ts
import { apiClient } from "@/lib/api/client";
import type {
  Preset,
  PresetCatalogResponse,
  PresetCreate,
  PresetUpdate,
  PresetUsage,
  PresetType,
} from "@/types/preset";

/**
 * Service for the platform-admin voice-engine preset catalog
 * (`/api/v1/presets`, `backend/src/voice_agents/preset_routes.py`).
 *
 * Mirrors the platform-tools catalog contract: CRUD + publish/unpublish +
 * usage + delete-with-`force` is `platform_admin` only; listing/fetch of
 * published presets is available to any authenticated user (org admins pick a
 * preset when configuring an agent). Drafts are platform-admin-only
 * (`include_drafts=true` is rejected with 403 for non-admins on the backend).
 *
 * Presets carry no secrets; per-provider API keys live on the organization.
 * All methods return the unwrapped `.data` on success and throw on non-2xx
 * (the `apiClient` normalizes errors, including the 409 `in_use` detail object,
 * into a thrown `Error`).
 */
class PresetService {
  private baseUrl = "/api/v1/presets";

  /**
   * List presets visible to the caller.
   *
   * Org users see only **published** rows by default — the catalog they pick
   * from when configuring an agent. Platform admins pass `{ includeDrafts: true }`
   * to also see drafts they are authoring; the backend rejects a non-admin that
   * sets it (403). `presetType` filters by `realtime` | `pipeline`.
   */
  async listPresets(opts?: {
    presetType?: PresetType;
    includeDrafts?: boolean;
  }): Promise<Preset[]> {
    const params = new URLSearchParams();
    if (opts?.presetType) params.set("preset_type", opts.presetType);
    if (opts?.includeDrafts) params.set("include_drafts", "true");
    const query = params.toString();
    const response = await apiClient.get<Preset[]>(
      `${this.baseUrl}/${query ? `?${query}` : ""}`,
    );
    return response.data;
  }

  /**
   * Fetch the org-facing white-label voice profile catalog with readiness flags.
   *
   * Returns display metadata only (no `config` or engine/provider details).
   * Pass `organizationId` and optionally `usePlatformCredits` (mirrors the
   * per-agent billing toggle) so the backend can compute `is_ready` per profile.
   */
  async getPresetCatalog(opts: {
    organizationId: string;
    usePlatformCredits?: boolean;
  }): Promise<PresetCatalogResponse> {
    const params = new URLSearchParams({
      organization_id: opts.organizationId,
    });
    if (opts.usePlatformCredits) {
      params.set("use_platform_credits", "true");
    }
    const response = await apiClient.get<PresetCatalogResponse>(
      `${this.baseUrl}/catalog?${params.toString()}`,
    );
    return response.data;
  }

  /** Fetch a single preset by id (drafts are platform-admin-only on the backend). */
  async getPreset(presetId: string): Promise<Preset> {
    const response = await apiClient.get<Preset>(`${this.baseUrl}/${presetId}`);
    return response.data;
  }

  /**
   * Fetch the current platform default preset (platform-admin only).
   *
   * The default is the fallback config an agent uses when it has no preset
   * selected (`preset_id` null). It is published and appears as the dynamic
   * default option in the org-admin picker. Returns 404 if no default row is
   * designated (the worker then falls back to the hardcoded realtime default).
   */
  async getDefaultPreset(): Promise<Preset> {
    const response = await apiClient.get<Preset>(`${this.baseUrl}/default`);
    return response.data;
  }

  /**
   * Replace the current platform default's `config` via the legacy endpoint.
   *
   * The request body is the raw `SpeechConfig` dict (realtime or pipeline); the
   * backend re-validates it and re-derives `preset_type`. Only `config` and
   * the derived `preset_type` are written. Use the id-based preset update to
   * edit metadata; a default must remain published and platform-managed.
   * Returns 400 on an invalid config, 404 if no default row exists.
   */
  async updateDefaultPreset(config: Record<string, unknown>): Promise<Preset> {
    const response = await apiClient.put<Preset>(
      `${this.baseUrl}/default`,
      config,
    );
    return response.data;
  }

  /**
   * Create or replace a preset by name (upsert). The new preset starts as a
   * draft unless `is_published` is set in the body; publish it via
   * `publishPreset`. The backend validates the `config` discriminated union
   * and derives `preset_type` from `config.engine_mode`.
   */
  async createPreset(payload: PresetCreate): Promise<Preset> {
    const response = await apiClient.post<Preset>(`${this.baseUrl}/`, payload);
    return response.data;
  }

  /** Partially update a preset (re-validates `config` and re-derives `preset_type`). */
  async updatePreset(presetId: string, payload: PresetUpdate): Promise<Preset> {
    const response = await apiClient.put<Preset>(
      `${this.baseUrl}/${presetId}`,
      payload,
    );
    return response.data;
  }

  /**
   * Publish or unpublish a preset (platform-admin only). Publishing flips
   * `is_published` to true, surfacing the preset in every org's preset picker;
   * unpublishing hides it from new assignments (agents already using it keep
   * working — the worker reads the preset by id, not via the listing).
   */
  async publishPreset(presetId: string, published: boolean): Promise<Preset> {
    const endpoint = published ? "publish" : "unpublish";
    const response = await apiClient.post<Preset>(
      `${this.baseUrl}/${presetId}/${endpoint}`,
    );
    return response.data;
  }

  /** Select a published platform-managed profile as the global default. */
  async setDefaultPreset(presetId: string): Promise<Preset> {
    const response = await apiClient.post<Preset>(
      `${this.baseUrl}/${presetId}/default`,
    );
    return response.data;
  }

  /**
   * Delete a preset (platform-admin only).
   *
   * Guardrail: a preset referenced by any agent is refused with 409 `in_use`
   * unless `force` is set. With `force`, the `voice_agents.preset_id` FK
   * `ON DELETE SET NULL` drops referencing agents back to the current platform default.
   * The UI pre-fetches usage via `getPresetUsage` and passes `force = count > 0`
   * after a type-to-confirm dialog, so the 409 path is a backend safety net.
   */
  async deletePreset(presetId: string, force = false): Promise<void> {
    const query = force ? "?force=true" : "";
    await apiClient.delete(`${this.baseUrl}/${presetId}${query}`);
  }

  /**
   * List the agents currently using a preset (platform-admin only). Powers the
   * delete-confirm dialog's "used by N agents" warning list and the unpublish
   * banner. Returns `{ count, agents[] }`.
   */
  async getPresetUsage(presetId: string): Promise<PresetUsage> {
    const response = await apiClient.get<PresetUsage>(
      `${this.baseUrl}/${presetId}/usage`,
    );
    return response.data;
  }
}

export const presetService = new PresetService();
