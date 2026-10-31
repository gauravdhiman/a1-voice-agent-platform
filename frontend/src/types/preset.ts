/**
 * Voice-engine preset type definitions.
 *
 * Mirrors the backend Pydantic models in `shared/voice_agents/preset_models.py`.
 * A **preset** is a named, platform-admin-managed voice-engine configuration.
 * An agent references one preset by `preset_id`; voice-ws fetches the preset
 * row live on every call (no versioning — admin edits take effect on the next
 * call). Presets carry **no secrets**; `credential_source` chooses between
 * platform-configured provider keys and per-organization keys stored in the
 * encrypted `organizations.provider_credentials` column.
 *
 * Two preset types only — `realtime` / `pipeline` — matching the `SpeechConfig`
 * discriminated union (`shared/voice_agents/speech_config.py`). Legacy DB rows
 * may still contain the removed `livekit_inference` provider slug on a stage;
 * migration rewrites those to direct providers. `preset_type` is a denormalized
 * filter column derived from `config.engine_mode` on every write by the backend
 * — never set by hand.
 *
 * The frontend does **not** re-validate the `config` discriminated union; the
 * backend validates it on create/update (`preset_routes.py` → `preset_service`
 * → `parse_speech_config`). `config` is therefore typed as an opaque
 * `Record<string, unknown>` here.
 */

/**
 * The engine mode a preset configures (mirrors backend `PresetType` / `EngineMode`).
 *
 * - `realtime` — end-to-end speech model (Google Gemini native-audio).
 * - `pipeline` — modular STT -> LLM -> TTS cascade, each stage swappable.
 */
export type PresetType = "realtime" | "pipeline";

/** Credential boundary for a reusable voice profile. */
export type PresetCredentialSource = "platform" | "organization";

/**
 * Fallback display before the catalog response arrives. The server returns the
 * selected platform preset's actual name and description after loading.
 */
export const DEFAULT_PRESET_DISPLAY = {
  name: "Platform default",
  description: "Used when an agent has no voice profile selected.",
} as const;

/**
 * A platform-admin-managed voice-engine preset (API response shape).
 *
 * `preset_type` is derived from `config.engine_mode` by the backend on every
 * write; it is never accepted as input (`extra="forbid"` rejects a hand-set
 * `preset_type`).
 */
export interface Preset {
  id: string;
  name: string;
  description: string | null;
  /** The validated SpeechConfig (realtime or pipeline). Opaque on the frontend. */
  config: Record<string, unknown>;
  is_published: boolean;
  /** Provider key boundary selected by the platform admin. */
  credential_source: PresetCredentialSource;
  /** Derived from `config.engine_mode` by the backend; never an input field. */
  preset_type: PresetType;
  /**
   * True for the published platform preset used by agents with no explicit
   * `preset_id`. Response-only; the backend sets it and does not accept input.
   */
  is_default: boolean;
  created_at: string;
  updated_at: string;
}

/** Request body for `POST /api/v1/presets/` (upsert by name). */
export interface PresetCreate {
  name: string;
  description?: string | null;
  /** The SpeechConfig dict (realtime or pipeline). Validated server-side. */
  config: Record<string, unknown>;
  is_published?: boolean;
  credential_source?: PresetCredentialSource;
}

/** Request body for `PUT /api/v1/presets/{id}` (all fields optional). */
export interface PresetUpdate {
  name?: string;
  description?: string | null;
  config?: Record<string, unknown>;
  is_published?: boolean;
  credential_source?: PresetCredentialSource;
}

/**
 * A single agent referencing a preset (the delete-guardrail listing).
 *
 * Mirrors backend `PresetUsageAgent`. Field names use snake_case to match the
 * API response (`shared/voice_agents/preset_models.py`).
 */
export interface PresetUsageAgent {
  id: string;
  name: string;
  organization_id: string;
}

/** Result of `GET /api/v1/presets/{id}/usage` — used-by-N-agents guardrail. */
export interface PresetUsage {
  count: number;
  agents: PresetUsageAgent[];
}

/**
 * Org-facing voice profile entry (white-label catalog).
 *
 * Mirrors backend `PresetCatalogItem` — no `config`, `preset_type`, or provider
 * names. Readiness is org-scoped and computed server-side.
 */
export interface PresetCatalogItem {
  id: string;
  name: string;
  description: string | null;
  credential_source: PresetCredentialSource;
  /** True when this profile is fully configured for the requesting org. */
  is_ready: boolean;
}

/**
 * Org-facing catalog response from `GET /api/v1/presets/catalog`.
 *
 * Includes readiness for published profiles and the current platform default.
 * `default_is_ready` reflects the platform keys required by that default.
 * `credentials_self_service` drives generic setup copy
 * (self-serve vs contact platform admin).
 */
export interface PresetCatalogResponse {
  presets: PresetCatalogItem[];
  default: {
    name: string;
    description: string | null;
    credential_source: "platform";
    is_ready: boolean;
  } | null;
  default_is_ready: boolean;
  credentials_self_service: boolean;
}
