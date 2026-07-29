/**
 * Pure helpers for authoring a preset's `SpeechConfig` in the platform-admin
 * preset author form.
 *
 * The backend stores a `SpeechConfig` discriminated union
 * (`shared/voice_agents/speech_config.py`) on each preset row, validated with
 * `extra="forbid"` — so the object emitted here must contain **exactly** the
 * keys the backend model accepts and no others. These builders are pure
 * (string form-state in -> config object out) so they are unit-testable
 * without rendering React.
 *
 * Two engine modes:
 *  - `realtime`  — a single end-to-end Google Gemini native-audio model.
 *  - `pipeline`  — modular STT -> LLM -> TTS cascade (+ optional VAD). A
 *    "mixed" preset is just a pipeline where some stages use LiveKit Inference
 *    (`provider: "livekit_inference"`) and some use direct providers.
 *
 * `turn_detection` is intentionally omitted (Phase 5). `vad` is omitted when the
 * admin leaves it unconfigured (the backend default `None` applies; the worker
 * still builds an explicit Silero VAD regardless).
 */

/** Provider dispatch keys selectable per pipeline stage. */
export const STT_PROVIDERS = ["deepgram", "livekit_inference"] as const;
export const LLM_PROVIDERS = [
  "openai",
  "cerebras",
  "livekit_inference",
] as const;
export const TTS_PROVIDERS = ["cartesia", "livekit_inference"] as const;
export const VAD_PROVIDERS = ["silero"] as const;

/** Default realtime field values — mirror `speech_config.py` constants. */
export const DEFAULT_REALTIME_MODEL =
  "gemini-2.5-flash-native-audio-preview-12-2025";
export const DEFAULT_REALTIME_VOICE = "Puck";
export const DEFAULT_REALTIME_TEMPERATURE = 0.7;
export const DEFAULT_REALTIME_SILENCE_MS = 500;
export const DEFAULT_REALTIME_PREFIX_MS = 200;

export interface RealtimeFormState {
  model: string;
  voice: string;
  temperature: string; // numeric input kept as string; coerced on build
  silence_duration_ms: string;
  prefix_padding_ms: string;
  /** Raw JSON textarea for `params` (rarely used; reserved kwargs). */
  paramsText: string;
}

export interface StageFormState {
  provider: string;
  /** Blank = omit (provider default model applies). */
  model: string;
  /** Raw JSON textarea for provider-specific `params` kwargs. */
  paramsText: string;
}

export interface PipelineFormState {
  stt: StageFormState;
  llm: StageFormState;
  tts: StageFormState;
  /** When null, the VAD stage is omitted entirely (backend default). */
  vad: StageFormState | null;
}

export type EngineMode = "realtime" | "pipeline";

/** A blank realtime form seeded with the backend defaults. */
export function defaultRealtimeForm(): RealtimeFormState {
  return {
    model: DEFAULT_REALTIME_MODEL,
    voice: DEFAULT_REALTIME_VOICE,
    temperature: String(DEFAULT_REALTIME_TEMPERATURE),
    silence_duration_ms: String(DEFAULT_REALTIME_SILENCE_MS),
    prefix_padding_ms: String(DEFAULT_REALTIME_PREFIX_MS),
    paramsText: "",
  };
}

/** A blank pipeline form: Deepgram STT + OpenAI LLM + Cartesia TTS, no VAD. */
export function defaultPipelineForm(): PipelineFormState {
  const blankStage = (provider: string): StageFormState => ({
    provider,
    model: "",
    paramsText: "",
  });
  return {
    stt: blankStage("deepgram"),
    llm: blankStage("openai"),
    tts: blankStage("cartesia"),
    vad: null,
  };
}

/**
 * Parse a raw JSON `params` textarea into a dict.
 *
 * Blank text -> `{}` (no error). Invalid JSON -> `{}` plus an error message so
 * the form can block submit and show the user what to fix. Non-object JSON
 * (e.g. a bare string) is also an error — `params` must be an object.
 */
export function parseParams(
  text: string,
): { params: Record<string, unknown>; error: string | null } {
  const trimmed = text.trim();
  if (!trimmed) return { params: {}, error: null };
  try {
    const parsed: unknown = JSON.parse(trimmed);
    if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
      return { params: {}, error: "params must be a JSON object" };
    }
    return { params: parsed as Record<string, unknown>, error: null };
  } catch {
    return { params: {}, error: "params is not valid JSON" };
  }
}

/** Build a single pipeline stage config (`{provider, model?, params}`). */
export function buildStage(stage: StageFormState): Record<string, unknown> {
  const { params } = parseParams(stage.paramsText);
  const out: Record<string, unknown> = {
    provider: stage.provider,
    params,
  };
  // `model` is Optional[str] on the backend; omit when blank so the provider's
  // default model applies (the worker builder passes `model` only when set).
  if (stage.model.trim() !== "") {
    out.model = stage.model.trim();
  }
  return out;
}

/** Coerce a numeric string to a number, falling back to the default on blank. */
function toNumber(value: string, fallback: number): number {
  const n = Number(value);
  return value.trim() === "" || Number.isNaN(n) ? fallback : n;
}

/** Build a `RealtimeSpeechConfig` dict from the realtime form state. */
export function buildRealtimeConfig(
  s: RealtimeFormState,
): Record<string, unknown> {
  const { params, error } = parseParams(s.paramsText);
  if (error) {
    // The form should gate submit before calling this, but stay safe: drop the
    // invalid params and emit a valid config rather than throwing.
  }
  return {
    engine_mode: "realtime",
    provider: "google",
    model: s.model.trim() || DEFAULT_REALTIME_MODEL,
    voice: s.voice.trim() || DEFAULT_REALTIME_VOICE,
    temperature: toNumber(s.temperature, DEFAULT_REALTIME_TEMPERATURE),
    silence_duration_ms: toNumber(s.silence_duration_ms, DEFAULT_REALTIME_SILENCE_MS),
    prefix_padding_ms: toNumber(s.prefix_padding_ms, DEFAULT_REALTIME_PREFIX_MS),
    params,
  };
}

/**
 * Build a `PipelineSpeechConfig` dict from the pipeline form state. `vad` is
 * omitted when unconfigured (the backend default `None` applies).
 */
export function buildPipelineConfig(
  s: PipelineFormState,
): Record<string, unknown> {
  const out: Record<string, unknown> = {
    engine_mode: "pipeline",
    stt: buildStage(s.stt),
    llm: buildStage(s.llm),
    tts: buildStage(s.tts),
  };
  if (s.vad) {
    out.vad = buildStage(s.vad);
  }
  return out;
}

/** Build the full `SpeechConfig` dict for the active engine mode. */
export function buildSpeechConfig(
  mode: EngineMode,
  realtime: RealtimeFormState,
  pipeline: PipelineFormState,
): Record<string, unknown> {
  return mode === "realtime"
    ? buildRealtimeConfig(realtime)
    : buildPipelineConfig(pipeline);
}

/**
 * Best-effort parse of an existing `SpeechConfig` dict back into form state
 * (used to prefill the author form when editing a preset). Unknown shapes fall
 * back to defaults so the admin always sees a valid, editable form.
 */
export function formStateFromConfig(
  config: Record<string, unknown> | null | undefined,
): {
  mode: EngineMode;
  realtime: RealtimeFormState;
  pipeline: PipelineFormState;
} {
  const mode: EngineMode =
    config && config.engine_mode === "pipeline" ? "pipeline" : "realtime";
  const realtime = defaultRealtimeForm();
  const pipeline = defaultPipelineForm();
  if (!config || typeof config !== "object") {
    return { mode, realtime, pipeline };
  }
  if (mode === "realtime") {
    const c = config as Record<string, unknown>;
    if (typeof c.model === "string") realtime.model = c.model;
    if (typeof c.voice === "string") realtime.voice = c.voice;
    if (c.temperature !== undefined) realtime.temperature = String(c.temperature);
    if (c.silence_duration_ms !== undefined)
      realtime.silence_duration_ms = String(c.silence_duration_ms);
    if (c.prefix_padding_ms !== undefined)
      realtime.prefix_padding_ms = String(c.prefix_padding_ms);
    if (c.params && typeof c.params === "object")
      realtime.paramsText = JSON.stringify(c.params, null, 2);
  } else {
    const c = config as Record<string, unknown>;
    const toStage = (key: string): StageFormState => {
      const raw = c[key] as Record<string, unknown> | undefined;
      if (!raw || typeof raw !== "object") return { provider: "", model: "", paramsText: "" };
      return {
        provider: typeof raw.provider === "string" ? raw.provider : "",
        model: typeof raw.model === "string" ? raw.model : "",
        paramsText:
          raw.params && typeof raw.params === "object"
            ? JSON.stringify(raw.params, null, 2)
            : "",
      };
    };
    pipeline.stt = toStage("stt");
    pipeline.llm = toStage("llm");
    pipeline.tts = toStage("tts");
    const vadRaw = c.vad as Record<string, unknown> | null | undefined;
    if (vadRaw && typeof vadRaw === "object") {
      pipeline.vad = {
        provider: typeof vadRaw.provider === "string" ? vadRaw.provider : "silero",
        model: typeof vadRaw.model === "string" ? vadRaw.model : "",
        paramsText:
          vadRaw.params && typeof vadRaw.params === "object"
            ? JSON.stringify(vadRaw.params, null, 2)
            : "",
      };
    } else {
      pipeline.vad = null;
    }
  }
  return { mode, realtime, pipeline };
}