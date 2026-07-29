/**
 * Voice-engine preset type definitions.
 *
 * Mirrors the backend Pydantic models in `shared/voice_agents/preset_models.py`.
 * A **preset** is a named, platform-admin-managed voice-engine configuration.
 * An agent references one preset by `preset_id`; the worker fetches the preset
 * row live on every call (no versioning — admin edits take effect on the next
 * call). Presets carry **no secrets**; per-provider API keys live on the
 * organization (`organizations.provider_credentials`, encrypted).
 *
 * Two preset types only — `realtime` / `pipeline` — matching the `SpeechConfig`
 * discriminated union (`shared/voice_agents/speech_config.py`). A "mixed" preset
 * is NOT a third type: it is a `pipeline` preset where some stages use LiveKit
 * Inference and some use direct providers. `preset_type` is a denormalized
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
  /** Derived from `config.engine_mode` by the backend; never an input field. */
  preset_type: PresetType;
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
}

/** Request body for `PUT /api/v1/presets/{id}` (all fields optional). */
export interface PresetUpdate {
  name?: string;
  description?: string | null;
  config?: Record<string, unknown>;
  is_published?: boolean;
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