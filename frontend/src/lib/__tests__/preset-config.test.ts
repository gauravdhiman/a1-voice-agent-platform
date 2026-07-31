/**
 * Unit tests for the preset `SpeechConfig` builder (`@/lib/preset-config`).
 *
 * These pin the exact object shape the platform-admin author form emits, which
 * the backend validates with `extra="forbid"` (see
 * `shared/voice_agents/speech_config.py`). Any stray key or wrong type would be
 * rejected with 400, so the builders must emit precisely the accepted fields.
 */
import { describe, expect, it } from "vitest";

import {
  buildPipelineConfig,
  buildRealtimeConfig,
  buildSpeechConfig,
  buildStage,
  buildTtsStage,
  defaultPipelineForm,
  defaultRealtimeForm,
  formStateFromConfig,
  parseParams,
} from "@/lib/preset-config";

describe("parseParams", () => {
  it("blank text -> empty object, no error", () => {
    expect(parseParams("")).toEqual({ params: {}, error: null });
    expect(parseParams("   ")).toEqual({ params: {}, error: null });
  });

  it("valid JSON object -> parsed, no error", () => {
    const { params, error } = parseParams('{"language":"en","keywords":["hi"]}');
    expect(error).toBeNull();
    expect(params).toEqual({ language: "en", keywords: ["hi"] });
  });

  it("invalid JSON -> empty object + error", () => {
    const { params, error } = parseParams("{not json");
    expect(params).toEqual({});
    expect(error).toMatch(/not valid JSON/);
  });

  it("non-object JSON (array / bare string) -> error", () => {
    expect(parseParams("[1,2]").error).toMatch(/JSON object/);
    expect(parseParams('"hello"').error).toMatch(/JSON object/);
  });
});

describe("buildStage", () => {
  it("omits blank model and forwards params", () => {
    const stage = buildStage({
      provider: "deepgram",
      model: "",
      paramsText: '{"language":"en-US"}',
    });
    expect(stage).toEqual({
      provider: "deepgram",
      params: { language: "en-US" },
    });
    expect("model" in stage).toBe(false);
  });

  it("includes model when set", () => {
    const stage = buildStage({
      provider: "openai",
      model: "gpt-4.1",
      paramsText: "",
    });
    expect(stage).toEqual({ provider: "openai", model: "gpt-4.1", params: {} });
  });

  it("livekit_inference provider is a normal stage value", () => {
    const stage = buildStage({
      provider: "livekit_inference",
      model: "deepgram-nova-3",
      paramsText: "",
    });
    expect(stage.provider).toBe("livekit_inference");
  });
});

describe("buildTtsStage", () => {
  it("emits voice as a top-level field when set", () => {
    const stage = buildTtsStage({
      provider: "cartesia",
      model: "sonic-3",
      voice: "voice-uuid-abc",
      paramsText: '{"language":"en"}',
    });
    expect(stage).toEqual({
      provider: "cartesia",
      model: "sonic-3",
      voice: "voice-uuid-abc",
      params: { language: "en" },
    });
  });

  it("omits voice when blank and strips voice from params JSON", () => {
    const stage = buildTtsStage({
      provider: "cartesia",
      model: "",
      voice: "",
      paramsText: '{"voice":"legacy-in-params","speed":1.1}',
    });
    expect(stage).toEqual({
      provider: "cartesia",
      params: { speed: 1.1 },
    });
    expect("voice" in stage).toBe(false);
  });

  it("dedicated voice field wins over params.voice on emit", () => {
    const stage = buildTtsStage({
      provider: "livekit_inference",
      model: "cartesia/sonic-3",
      voice: "field-voice",
      paramsText: '{"voice":"params-voice","speed":1.0}',
    });
    expect(stage.voice).toBe("field-voice");
    expect(stage.params).toEqual({ speed: 1.0 });
  });
});

describe("buildRealtimeConfig", () => {
  it("emits the exact accepted shape with defaults", () => {
    const cfg = buildRealtimeConfig(defaultRealtimeForm());
    expect(cfg).toEqual({
      engine_mode: "realtime",
      provider: "google",
      model: "gemini-2.5-flash-native-audio-preview-12-2025",
      voice: "Puck",
      temperature: 0.7,
      silence_duration_ms: 500,
      prefix_padding_ms: 200,
      params: {},
    });
  });

  it("coerces numeric strings to numbers", () => {
    const cfg = buildRealtimeConfig({
      model: "custom-model",
      voice: "Charon",
      temperature: "0.3",
      silence_duration_ms: "300",
      prefix_padding_ms: "100",
      paramsText: '{"foo":"bar"}',
    });
    expect(cfg.temperature).toBe(0.3);
    expect(cfg.silence_duration_ms).toBe(300);
    expect(cfg.prefix_padding_ms).toBe(100);
    expect(cfg.model).toBe("custom-model");
    expect(cfg.voice).toBe("Charon");
    expect(cfg.params).toEqual({ foo: "bar" });
  });

  it("falls back to defaults on blank numeric fields", () => {
    const cfg = buildRealtimeConfig({
      model: "",
      voice: "",
      temperature: "",
      silence_duration_ms: "",
      prefix_padding_ms: "",
      paramsText: "",
    });
    expect(cfg.model).toBe("gemini-2.5-flash-native-audio-preview-12-2025");
    expect(cfg.voice).toBe("Puck");
    expect(cfg.temperature).toBe(0.7);
    expect(cfg.silence_duration_ms).toBe(500);
    expect(cfg.prefix_padding_ms).toBe(200);
  });

  it("never emits stray keys (extra=forbid safe)", () => {
    const cfg = buildRealtimeConfig(defaultRealtimeForm());
    expect(Object.keys(cfg).sort()).toEqual(
      [
        "engine_mode",
        "params",
        "prefix_padding_ms",
        "provider",
        "silence_duration_ms",
        "model",
        "temperature",
        "voice",
      ].sort(),
    );
  });
});

describe("buildPipelineConfig", () => {
  it("emits stt/llm/tts and omits vad when unconfigured", () => {
    const cfg = buildPipelineConfig(defaultPipelineForm());
    expect(cfg.engine_mode).toBe("pipeline");
    expect(cfg.stt).toEqual({ provider: "deepgram", params: {} });
    expect(cfg.llm).toEqual({ provider: "openai", params: {} });
    expect(cfg.tts).toEqual({ provider: "cartesia", params: {} });
    expect("vad" in cfg).toBe(false);
    expect("turn_detection" in cfg).toBe(false);
  });

  it("includes vad when configured", () => {
    const form = defaultPipelineForm();
    form.vad = { provider: "silero", model: "", paramsText: "" };
    const cfg = buildPipelineConfig(form);
    expect(cfg.vad).toEqual({ provider: "silero", params: {} });
  });

  it("supports a mixed Inference + direct preset", () => {
    const form = defaultPipelineForm();
    form.stt = { provider: "livekit_inference", model: "deepgram-nova-3", paramsText: "" };
    form.llm = { provider: "cerebras", model: "llama-4-scout-17b-16e-instruct", paramsText: "" };
    form.tts = {
      provider: "livekit_inference",
      model: "cartesia-sonic",
      voice: "",
      paramsText: "",
    };
    const cfg = buildPipelineConfig(form);
    expect(cfg.stt).toEqual({
      provider: "livekit_inference",
      model: "deepgram-nova-3",
      params: {},
    });
    expect(cfg.llm).toEqual({
      provider: "cerebras",
      model: "llama-4-scout-17b-16e-instruct",
      params: {},
    });
    expect(cfg.tts).toEqual({
      provider: "livekit_inference",
      model: "cartesia-sonic",
      params: {},
    });
  });

  it("never emits stray keys (extra=forbid safe)", () => {
    const cfg = buildPipelineConfig(defaultPipelineForm());
    expect(Object.keys(cfg).sort()).toEqual(
      ["engine_mode", "llm", "stt", "tts"].sort(),
    );
  });
});

describe("buildSpeechConfig", () => {
  it("dispatches on engine mode", () => {
    const realtime = buildSpeechConfig("realtime", defaultRealtimeForm(), defaultPipelineForm());
    const pipeline = buildSpeechConfig("pipeline", defaultRealtimeForm(), defaultPipelineForm());
    expect(realtime.engine_mode).toBe("realtime");
    expect(pipeline.engine_mode).toBe("pipeline");
    expect(realtime.provider).toBe("google");
    expect(pipeline.stt).toBeDefined();
  });
});

describe("formStateFromConfig (edit prefill)", () => {
  it("round-trips a realtime config", () => {
    const cfg = buildRealtimeConfig({
      model: "m",
      voice: "v",
      temperature: "0.4",
      silence_duration_ms: "250",
      prefix_padding_ms: "150",
      paramsText: '{"x":1}',
    });
    const { mode, realtime } = formStateFromConfig(cfg);
    expect(mode).toBe("realtime");
    expect(realtime.model).toBe("m");
    expect(realtime.voice).toBe("v");
    expect(realtime.temperature).toBe("0.4");
    expect(realtime.paramsText).toContain('"x": 1');
  });

  it("round-trips a pipeline config with vad", () => {
    const form = defaultPipelineForm();
    form.llm.model = "gpt-4.1";
    form.vad = { provider: "silero", model: "", paramsText: "" };
    const cfg = buildPipelineConfig(form);
    const { mode, pipeline } = formStateFromConfig(cfg);
    expect(mode).toBe("pipeline");
    expect(pipeline.llm.model).toBe("gpt-4.1");
    expect(pipeline.vad).not.toBeNull();
    expect(pipeline.vad?.provider).toBe("silero");
  });

  it("round-trips a pipeline config with tts voice", () => {
    const form = defaultPipelineForm();
    form.tts.voice = "voice-uuid-123";
    form.tts.paramsText = '{"language":"en"}';
    const cfg = buildPipelineConfig(form);
    const { pipeline } = formStateFromConfig(cfg);
    expect(pipeline.tts.voice).toBe("voice-uuid-123");
    expect(pipeline.tts.paramsText).toContain('"language": "en"');
  });

  it("hoists legacy params.voice into the tts voice field on prefill", () => {
    const { pipeline } = formStateFromConfig({
      engine_mode: "pipeline",
      stt: { provider: "deepgram", params: {} },
      llm: { provider: "openai", params: {} },
      tts: {
        provider: "cartesia",
        params: { voice: "legacy-uuid", speed: 1.0 },
      },
    });
    expect(pipeline.tts.voice).toBe("legacy-uuid");
    expect(pipeline.tts.paramsText).toContain('"speed": 1');
    expect(pipeline.tts.paramsText).not.toContain("legacy-uuid");
  });

  it("falls back to defaults for null/unknown config", () => {
    const { mode, realtime, pipeline } = formStateFromConfig(null);
    expect(mode).toBe("realtime");
    expect(realtime.model).toBe("gemini-2.5-flash-native-audio-preview-12-2025");
    expect(pipeline.stt.provider).toBe("deepgram");
  });
});