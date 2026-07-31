/**
 * Unit tests for `presetService` (`@/services/preset-service`).
 *
 * Asserts each method hits the right `/api/v1/presets` endpoint with the right
 * HTTP verb, query string, and body — and returns the unwrapped `.data`. The
 * `apiClient` is mocked so no network call is made.
 */
import { beforeEach, describe, expect, it, vi } from "vitest";

// `vi.hoisted` runs before the hoisted `vi.mock` factory, so the mock object is
// initialized in time for the factory to reference it.
const { apiClient } = vi.hoisted(() => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

vi.mock("@/lib/api/client", () => ({
  apiClient,
}));

import { presetService } from "@/services/preset-service";
import type { Preset } from "@/types/preset";

const PRESET: Preset = {
  id: "p-1",
  name: "Realtime (Gemini)",
  description: "Default realtime profile",
  config: { engine_mode: "realtime", provider: "google" },
  is_published: true,
  preset_type: "realtime",
  is_default: false,
  created_at: "2026-07-29T00:00:00Z",
  updated_at: "2026-07-29T00:00:00Z",
};

const DEFAULT_PRESET: Preset = {
  id: "p-default",
  name: "System Default",
  description: "The fallback voice profile.",
  config: { engine_mode: "realtime", provider: "google" },
  is_published: false,
  preset_type: "realtime",
  is_default: true,
  created_at: "2026-07-29T00:00:00Z",
  updated_at: "2026-07-29T00:00:00Z",
};

function resp<T>(data: T) {
  return { data };
}

describe("presetService", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("listPresets: GET / with no opts", async () => {
    apiClient.get.mockResolvedValue(resp([PRESET]));
    const out = await presetService.listPresets();
    expect(apiClient.get).toHaveBeenCalledWith("/api/v1/presets/");
    expect(out).toEqual([PRESET]);
  });

  it("listPresets: forwards preset_type + include_drafts as query params", async () => {
    apiClient.get.mockResolvedValue(resp([]));
    await presetService.listPresets({
      presetType: "pipeline",
      includeDrafts: true,
    });
    expect(apiClient.get).toHaveBeenCalledWith(
      "/api/v1/presets/?preset_type=pipeline&include_drafts=true",
    );
  });

  it("getPresetCatalog: GET /catalog with organization_id and use_platform_credits", async () => {
    const catalog = {
      presets: [
        {
          id: "p-1",
          name: "Professional Voice",
          description: null,
          is_ready: true,
        },
      ],
      default_is_ready: true,
      credentials_self_service: true,
    };
    apiClient.get.mockResolvedValue(resp(catalog));
    const out = await presetService.getPresetCatalog({
      organizationId: "org-1",
      usePlatformCredits: true,
    });
    expect(apiClient.get).toHaveBeenCalledWith(
      "/api/v1/presets/catalog?organization_id=org-1&use_platform_credits=true",
    );
    expect(out).toEqual(catalog);
  });

  it("getPreset: GET /{id}", async () => {
    apiClient.get.mockResolvedValue(resp(PRESET));
    const out = await presetService.getPreset("p-1");
    expect(apiClient.get).toHaveBeenCalledWith("/api/v1/presets/p-1");
    expect(out).toEqual(PRESET);
  });

  it("getDefaultPreset: GET /default", async () => {
    apiClient.get.mockResolvedValue(resp(DEFAULT_PRESET));
    const out = await presetService.getDefaultPreset();
    expect(apiClient.get).toHaveBeenCalledWith("/api/v1/presets/default");
    expect(out).toEqual(DEFAULT_PRESET);
  });

  it("updateDefaultPreset: PUT /default with the raw config as the body", async () => {
    apiClient.put.mockResolvedValue(resp(DEFAULT_PRESET));
    const config = { engine_mode: "pipeline", stt: { provider: "deepgram" }, llm: { provider: "openai" }, tts: { provider: "cartesia" } };
    const out = await presetService.updateDefaultPreset(config);
    // The body is the raw SpeechConfig dict itself (not wrapped in {config}).
    expect(apiClient.put).toHaveBeenCalledWith("/api/v1/presets/default", config);
    expect(out).toEqual(DEFAULT_PRESET);
  });

  it("createPreset: POST / with body", async () => {
    apiClient.post.mockResolvedValue(resp(PRESET));
    const body = { name: "Realtime (Gemini)", config: { engine_mode: "realtime" } };
    const out = await presetService.createPreset(body);
    expect(apiClient.post).toHaveBeenCalledWith("/api/v1/presets/", body);
    expect(out).toEqual(PRESET);
  });

  it("updatePreset: PUT /{id} with body", async () => {
    apiClient.put.mockResolvedValue(resp(PRESET));
    const body = { description: "updated" };
    await presetService.updatePreset("p-1", body);
    expect(apiClient.put).toHaveBeenCalledWith("/api/v1/presets/p-1", body);
  });

  it("publishPreset: POST /{id}/publish when published=true", async () => {
    apiClient.post.mockResolvedValue(resp({ ...PRESET, is_published: true }));
    await presetService.publishPreset("p-1", true);
    expect(apiClient.post).toHaveBeenCalledWith("/api/v1/presets/p-1/publish");
  });

  it("publishPreset: POST /{id}/unpublish when published=false", async () => {
    apiClient.post.mockResolvedValue(resp({ ...PRESET, is_published: false }));
    await presetService.publishPreset("p-1", false);
    expect(apiClient.post).toHaveBeenCalledWith("/api/v1/presets/p-1/unpublish");
  });

  it("deletePreset: DELETE /{id} with no force", async () => {
    apiClient.delete.mockResolvedValue(undefined);
    await presetService.deletePreset("p-1");
    expect(apiClient.delete).toHaveBeenCalledWith("/api/v1/presets/p-1");
  });

  it("deletePreset: DELETE /{id}?force=true when force=true", async () => {
    apiClient.delete.mockResolvedValue(undefined);
    await presetService.deletePreset("p-1", true);
    expect(apiClient.delete).toHaveBeenCalledWith("/api/v1/presets/p-1?force=true");
  });

  it("getPresetUsage: GET /{id}/usage", async () => {
    const usage = { count: 2, agents: [] };
    apiClient.get.mockResolvedValue(resp(usage));
    const out = await presetService.getPresetUsage("p-1");
    expect(apiClient.get).toHaveBeenCalledWith("/api/v1/presets/p-1/usage");
    expect(out).toEqual(usage);
  });
});