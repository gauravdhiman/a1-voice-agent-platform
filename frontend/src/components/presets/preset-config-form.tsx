"use client";

/**
 * `PresetConfigForm` — the platform-admin SpeechConfig authoring sub-form.
 *
 * This is the power-user surface where a platform admin assembles a preset's
 * `SpeechConfig` (realtime or pipeline). The admin DOES see the engine + stage
 * fields here; only the org user is shielded from them (the agent picker shows
 * just preset name + description).
 *
 * The form is controlled-at-a-distance: it owns its field state (seeded from
 * `initialConfig` on mount) and reports the built config + validity upward via
 * `onChange` / `onValidityChange`. The parent (the presets manager) stores the
 * latest config and enables Save/Publish only when valid. The pure builders in
 * `@/lib/preset-config` are unit-tested separately; this component is a thin
 * shell over them.
 *
 * The emitted object must satisfy the backend discriminated union
 * (`shared/voice_agents/speech_config.py`, `extra="forbid"`); `params` JSON
 * errors make the form invalid so an invalid config is never submitted.
 */
import React from "react";

import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  buildSpeechConfig,
  defaultRealtimeForm,
  formStateFromConfig,
  LLM_PROVIDERS,
  OPENAI_REALTIME_DEFAULT_MODEL,
  OPENAI_REALTIME_DEFAULT_VOICE,
  OPENAI_REALTIME_MODEL_VOICES,
  OPENAI_REALTIME_MODELS,
  parseParams,
  REALTIME_PROVIDERS,
  STT_PROVIDERS,
  TTS_PROVIDERS,
  VAD_PROVIDERS,
  type EngineMode,
  type PipelineFormState,
  type RealtimeFormState,
  type RealtimeProvider,
  type StageFormState,
  type TtsStageFormState,
} from "@/lib/preset-config";

interface PresetConfigFormProps {
  /** Existing config to prefill (edit mode); null/undefined starts fresh. */
  initialConfig?: Record<string, unknown> | null;
  /** Called with the built SpeechConfig on every change (valid or not). */
  onChange: (config: Record<string, unknown>) => void;
  /** Called with the overall validity (false when a params JSON is invalid). */
  onValidityChange?: (valid: boolean) => void;
}

const STAGE_PROVIDERS: Record<
  "stt" | "llm" | "tts" | "vad",
  readonly string[]
> = {
  stt: STT_PROVIDERS,
  llm: LLM_PROVIDERS,
  tts: TTS_PROVIDERS,
  vad: VAD_PROVIDERS,
};

/** A single pipeline stage editor (provider select + model + params). */
function StageEditor({
  stage,
  providers,
  label,
  onChange,
}: {
  stage: StageFormState;
  providers: readonly string[];
  label: string;
  onChange: (next: StageFormState) => void;
}) {
  const { error } = parseParams(stage.paramsText);
  return (
    <div className="form-section space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">{label}</span>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1">
          <Label className="text-xs">Provider</Label>
          <select
            className="form-control w-full rounded-md px-2 py-1 text-sm"
            value={stage.provider}
            onChange={(e) => onChange({ ...stage, provider: e.target.value })}
          >
            {providers.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
        </div>
        <div className="space-y-1">
          <Label className="text-xs">
            Model{" "}
            <span className="text-muted-foreground">(blank = default)</span>
          </Label>
          <Input
            value={stage.model}
            onChange={(e) => onChange({ ...stage, model: e.target.value })}
            placeholder="provider default"
            className="form-control"
          />
        </div>
      </div>
      <div className="space-y-1">
        <Label className="text-xs">
          Params <span className="text-muted-foreground">(JSON object)</span>
        </Label>
        <Textarea
          className="form-control font-mono text-xs"
          rows={2}
          value={stage.paramsText}
          onChange={(e) => onChange({ ...stage, paramsText: e.target.value })}
          placeholder='{"language": "en-US"}'
        />
        {error && <p className="text-xs text-destructive">{error}</p>}
      </div>
    </div>
  );
}

/** TTS stage editor with a dedicated voice field (Cartesia UUID, Inference voice, etc.). */
function TtsStageEditor({
  stage,
  providers,
  label,
  onChange,
}: {
  stage: TtsStageFormState;
  providers: readonly string[];
  label: string;
  onChange: (next: TtsStageFormState) => void;
}) {
  const { error } = parseParams(stage.paramsText);
  return (
    <div className="form-section space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">{label}</span>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1">
          <Label className="text-xs">Provider</Label>
          <select
            className="form-control w-full rounded-md px-2 py-1 text-sm"
            value={stage.provider}
            onChange={(e) => onChange({ ...stage, provider: e.target.value })}
          >
            {providers.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
        </div>
        <div className="space-y-1">
          <Label className="text-xs">
            Model{" "}
            <span className="text-muted-foreground">(blank = default)</span>
          </Label>
          <Input
            value={stage.model}
            onChange={(e) => onChange({ ...stage, model: e.target.value })}
            placeholder="provider default"
            className="form-control"
          />
        </div>
        <div className="space-y-1 col-span-2">
          <Label className="text-xs">
            Voice{" "}
            <span className="text-muted-foreground">
              (id, name, or UUID — blank = provider default)
            </span>
          </Label>
          <Input
            value={stage.voice}
            onChange={(e) => onChange({ ...stage, voice: e.target.value })}
            placeholder="e.g. Cartesia voice UUID or Inference voice id"
            className="form-control"
          />
        </div>
      </div>
      <div className="space-y-1">
        <Label className="text-xs">
          Params{" "}
          <span className="text-muted-foreground">
            (JSON object — language, speed, …)
          </span>
        </Label>
        <Textarea
          className="form-control font-mono text-xs"
          rows={2}
          value={stage.paramsText}
          onChange={(e) => onChange({ ...stage, paramsText: e.target.value })}
          placeholder='{"language": "en", "speed": 1.0}'
        />
        {error && <p className="text-xs text-destructive">{error}</p>}
      </div>
    </div>
  );
}

export function PresetConfigForm({
  initialConfig,
  onChange,
  onValidityChange,
}: PresetConfigFormProps) {
  const seeded = React.useMemo(
    () => formStateFromConfig(initialConfig ?? null),
    // Seed once on mount; subsequent edits live in local state.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  );
  const [mode, setMode] = React.useState<EngineMode>(seeded.mode);
  const [realtime, setRealtime] = React.useState<RealtimeFormState>(
    seeded.realtime,
  );
  const [pipeline, setPipeline] = React.useState<PipelineFormState>(
    seeded.pipeline,
  );

  // Recompute + report on every change. Validity = no params parse errors in
  // any visible stage (and the realtime params, when realtime mode is active).
  React.useEffect(() => {
    const config = buildSpeechConfig(mode, realtime, pipeline);
    let valid = true;
    const stages: StageFormState[] =
      mode === "pipeline"
        ? [
            pipeline.stt,
            pipeline.llm,
            pipeline.tts,
            ...(pipeline.vad ? [pipeline.vad] : []),
          ]
        : [];
    const allParams: string[] =
      mode === "realtime"
        ? [realtime.paramsText]
        : stages.map((s) => s.paramsText);
    for (const text of allParams) {
      if (parseParams(text).error) {
        valid = false;
        break;
      }
    }
    onChange(config);
    onValidityChange?.(valid);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode, realtime, pipeline]);

  const switchMode = (next: EngineMode) => {
    if (next === mode) return;
    setMode(next);
  };

  const switchRealtimeProvider = (provider: RealtimeProvider) => {
    setRealtime({
      ...defaultRealtimeForm(),
      provider,
      ...(provider === "openai"
        ? {
            model: OPENAI_REALTIME_DEFAULT_MODEL,
            voice: OPENAI_REALTIME_DEFAULT_VOICE,
          }
        : {}),
    });
  };

  const openAiVoices =
    realtime.provider === "openai" &&
    (OPENAI_REALTIME_MODELS as readonly string[]).includes(realtime.model)
      ? OPENAI_REALTIME_MODEL_VOICES[
          realtime.model as keyof typeof OPENAI_REALTIME_MODEL_VOICES
        ]
      : [];

  return (
    <div className="form-surface space-y-4">
      <div className="form-section space-y-1">
        <Label>Engine mode</Label>
        <div className="inline-flex rounded-md border">
          {(["realtime", "pipeline"] as const).map((m) => (
            <button
              key={m}
              type="button"
              onClick={() => switchMode(m)}
              className={`px-3 py-1 text-sm ${
                mode === m
                  ? "bg-primary text-primary-foreground"
                  : "bg-background hover:bg-muted"
              } ${m === "realtime" ? "rounded-l-md" : "rounded-r-md"}`}
            >
              {m === "realtime"
                ? "Realtime (end-to-end)"
                : "Pipeline (modular)"}
            </button>
          ))}
        </div>
        <p className="text-xs text-muted-foreground">
          {mode === "realtime"
            ? "One Google Gemini or OpenAI voice model handles STT + LLM + TTS."
            : "STT → LLM → TTS cascade; each stage swappable. A 'mixed' preset uses deprecated livekit_inference provider for some stages and direct providers for others."}
        </p>
      </div>

      {mode === "realtime" ? (
        <div className="form-surface space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div className="form-field space-y-1">
              <Label className="text-xs">Provider</Label>
              <select
                className="form-control w-full rounded-md px-2 py-1 text-sm"
                value={realtime.provider}
                onChange={(e) =>
                  switchRealtimeProvider(e.target.value as RealtimeProvider)
                }
              >
                {REALTIME_PROVIDERS.map((provider) => (
                  <option key={provider} value={provider}>
                    {provider === "google" ? "Google Gemini" : "OpenAI"}
                  </option>
                ))}
              </select>
            </div>
            <div className="form-field space-y-1">
              <Label className="text-xs">Model</Label>
              {realtime.provider === "openai" ? (
                <select
                  className="form-control w-full rounded-md px-2 py-1 text-sm"
                  value={realtime.model}
                  onChange={(e) => {
                    const model = e.target
                      .value as keyof typeof OPENAI_REALTIME_MODEL_VOICES;
                    const voices = OPENAI_REALTIME_MODEL_VOICES[model];
                    setRealtime({
                      ...realtime,
                      model,
                      voice: (voices as readonly string[]).includes(
                        realtime.voice,
                      )
                        ? realtime.voice
                        : OPENAI_REALTIME_DEFAULT_VOICE,
                    });
                  }}
                >
                  {OPENAI_REALTIME_MODELS.map((model) => (
                    <option key={model} value={model}>
                      {model}
                    </option>
                  ))}
                </select>
              ) : (
                <Input
                  value={realtime.model}
                  onChange={(e) =>
                    setRealtime({ ...realtime, model: e.target.value })
                  }
                  className="form-control"
                />
              )}
            </div>
            <div className="form-field space-y-1">
              <Label className="text-xs">Voice</Label>
              {realtime.provider === "openai" ? (
                <select
                  className="form-control w-full rounded-md px-2 py-1 text-sm"
                  value={realtime.voice}
                  onChange={(e) =>
                    setRealtime({ ...realtime, voice: e.target.value })
                  }
                >
                  {openAiVoices.map((voice) => (
                    <option key={voice} value={voice}>
                      {voice}
                    </option>
                  ))}
                </select>
              ) : (
                <Input
                  value={realtime.voice}
                  onChange={(e) =>
                    setRealtime({ ...realtime, voice: e.target.value })
                  }
                  className="form-control"
                />
              )}
            </div>
            {realtime.provider === "google" ? (
              <div className="form-field space-y-1">
                <Label className="text-xs">Temperature</Label>
                <Input
                  type="number"
                  step="0.1"
                  value={realtime.temperature}
                  onChange={(e) =>
                    setRealtime({ ...realtime, temperature: e.target.value })
                  }
                  className="form-control"
                />
              </div>
            ) : null}
            {realtime.provider === "google" ? (
              <div className="form-field space-y-1">
                <Label className="text-xs">Silence duration (ms)</Label>
                <Input
                  type="number"
                  value={realtime.silence_duration_ms}
                  onChange={(e) =>
                    setRealtime({
                      ...realtime,
                      silence_duration_ms: e.target.value,
                    })
                  }
                  className="form-control"
                />
              </div>
            ) : null}
            {realtime.provider === "google" ? (
              <div className="form-field space-y-1">
                <Label className="text-xs">Prefix padding (ms)</Label>
                <Input
                  type="number"
                  value={realtime.prefix_padding_ms}
                  onChange={(e) =>
                    setRealtime({
                      ...realtime,
                      prefix_padding_ms: e.target.value,
                    })
                  }
                  className="form-control"
                />
              </div>
            ) : null}
          </div>
          {realtime.provider === "google" ? (
            <div className="form-field space-y-1">
              <Label className="text-xs">
                Params{" "}
                <span className="text-muted-foreground">
                  (JSON object, reserved)
                </span>
              </Label>
              <Textarea
                className="form-control font-mono text-xs"
                rows={2}
                value={realtime.paramsText}
                onChange={(e) =>
                  setRealtime({ ...realtime, paramsText: e.target.value })
                }
                placeholder="{}"
              />
              {parseParams(realtime.paramsText).error && (
                <p className="text-xs text-destructive">
                  {parseParams(realtime.paramsText).error}
                </p>
              )}
            </div>
          ) : null}
        </div>
      ) : (
        <div className="form-surface space-y-3">
          <StageEditor
            label="STT (speech-to-text)"
            stage={pipeline.stt}
            providers={STAGE_PROVIDERS.stt}
            onChange={(stt) => setPipeline({ ...pipeline, stt })}
          />
          <StageEditor
            label="LLM (language model)"
            stage={pipeline.llm}
            providers={STAGE_PROVIDERS.llm}
            onChange={(llm) => setPipeline({ ...pipeline, llm })}
          />
          <TtsStageEditor
            label="TTS (text-to-speech)"
            stage={pipeline.tts}
            providers={STAGE_PROVIDERS.tts}
            onChange={(tts) => setPipeline({ ...pipeline, tts })}
          />
          {pipeline.vad ? (
            <StageEditor
              label="VAD (voice-activity detection) — optional"
              stage={pipeline.vad}
              providers={STAGE_PROVIDERS.vad}
              onChange={(vad) => setPipeline({ ...pipeline, vad })}
            />
          ) : null}
          <button
            type="button"
            className="text-xs text-muted-foreground underline"
            onClick={() =>
              setPipeline({
                ...pipeline,
                vad: pipeline.vad
                  ? null
                  : { provider: "silero", model: "", paramsText: "" },
              })
            }
          >
            {pipeline.vad ? "Remove VAD stage" : "+ Add VAD stage (optional)"}
          </button>
        </div>
      )}
    </div>
  );
}
