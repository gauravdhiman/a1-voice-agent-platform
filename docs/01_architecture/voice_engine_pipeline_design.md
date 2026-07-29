# Voice Engine: End-to-End + Pipeline Design (High-Level)

> Status: **Phases 1–3 complete** (Phases 1–2b behavior-neutral; Phase 3 makes the
> pipeline usable by agents). Phase 1 added the config models, `speech_providers/`
> package with the realtime provider behind a factory, the `session_builder` seam,
> and wired the worker through. Phase 2 wired the pipeline branch: per-stage
> LiveKit-native cloud providers (Silero VAD + Deepgram STT + OpenAI LLM +
> Cartesia TTS) behind a table-driven factory, with `turn_detection` deferred to
> Phase 5. Phase 2b added LiveKit **Inference** (STT/LLM/TTS through a single
> LiveKit Cloud auth, special dispatch path) and **Cerebras** (direct
> OpenAI-compatible LLM, keyed path), so a pipeline can mix Inference and direct
> stages per stage. **Phase 3** added platform-admin-managed **presets**
> (`pipeline_presets` catalog), per-agent `preset_id` (live fetch, no versioning),
> and a per-org **key resolver** backed by one encrypted
> `organizations.provider_credentials` blob. 100% coverage on the new shared
> modules; 95 backend + 45 worker Phase-3 tests green; no-network container smoke
> confirms the full key-resolution → Inference-injection seam. Live calls are
> unchanged for legacy agents (`preset_id=None` → realtime default). Phases 4–5
> pending. **The Phase 3 migration is reviewed but not yet run — awaits owner
> approval.**
>
> **Preset direction (locked in, landed in Phase 3):** configuration is exposed to
> org admins/users as **platform-admin-managed presets**, not a raw per-stage
> provider+model picker. Two preset types only — `{realtime, pipeline}` — a
> "mixed" preset is just a pipeline where some stages use Inference and some use
> direct providers (no third type). Agents **reference** a preset by id **only** —
> **no versioning**: the worker fetches the preset row live on every call, so an
> admin's edit takes effect on the next call. For LiveKit Inference, a tenant can
> **bring its own LiveKit key** (org-level, Inference-only for now, injected only
> when the preset uses an Inference stage) instead of consuming the platform's
> LiveKit plan — mirrors the existing Google-key BYO / `use_platform_credits`
> pattern; a future path migrates LiveKit rooms/sessions to tenant keys.
>
> Implementation doc (component reference, per-stage builders, tests):
> [`02_core_systems/voice_engine.md`](../02_core_systems/voice_engine.md)
>
> Goal: support **two configurable conversation engines** per agent — the existing
> Google end-to-end realtime model, **and** a modular STT → LLM → TTS pipeline where
> each stage can use a different provider/model. Reuse existing worker plumbing; keep
> it modular and swappable.

## Key decision (please confirm)

The HF `speech-to-speech` reference is **not** LiveKit — it is a custom
`threading.Queue` cascade behind a self-built OpenAI-Realtime WebSocket server, and the
`hf-realtime-voice` space is just a FastAPI metering gateway in front of it
(silero VAD → parakeet STT → Gemma-4-31B on Cerebras → Qwen3-TTS).

We are already on **LiveKit agents (asyncio)**. LiveKit's `AgentSession` natively
supports **both** modes by construction:

- End-to-end (today): `AgentSession(llm=RealtimeModel(...))`
- Pipeline (new): `AgentSession(stt=..., llm=..., tts=..., vad=..., turn_detection=...)`

**Recommendation: use LiveKit's native pipeline mode**, *not* a port of the HF queue
plumbing. This reuses 100% of our existing infrastructure (JobContext, `room_io`,
PromptBuilder, two-tier tools + MCP, room-name dispatch, greeting, API-key routing) and
keeps a single asyncio runtime. From the HF repo we borrow the **provider-factory
abstraction** and a small set of latency techniques LiveKit does not already provide.

```mermaid
flowchart LR
    subgraph HF["HuggingFace speech-to-speech (reference, NOT copied)"]
        A1["threading.Queue cascade"] --> A2["Custom OpenAI-Realtime WS server"]
    end
    subgraph Us["Our platform (LiveKit agents, asyncio)"]
        B1["Worker entrypoint"] --> B2["AgentSession"]
        B2 -->|"realtime mode"| B3["RealtimeModel (Google)"]
        B2 -->|"pipeline mode (new)"| B4["STT + LLM + TTS + VAD + TurnDetector"]
    end
    HF -. "borrow: factory pattern + latency tricks" .-> Us
```

---

## 1. Where the two modes diverge — one seam only

Everything upstream (room dispatch, agent fetch, prompt build, tool/MCP wiring,
API-key resolution) and downstream (room join, greeting, cleanup) is **shared and
unchanged**. The *only* divergence is **how the `AgentSession` is constructed**.

```mermaid
flowchart TD
    Call["Inbound call / test / embed room"] --> Dispatch["Room-name dispatch<br/>call_ / test_ / embed_"]
    Dispatch --> Fetch["voice_agent_service.get_agent_by_*"]
    Fetch --> Prompt["PromptBuilder.build (shared)"]
    Fetch --> Keys["Key resolver (shared, extended)"]
    Prompt --> Builder["session_builder.build_agent_session()<br/>THE SEAM"]
    Keys --> Builder
    Fetch --> Tools["Two-tier tools + MCP + skills (shared, mode-agnostic)"]
    Tools --> Agent["DynamicAgent(instructions, tools)"]
    Builder --> Session["AgentSession"]
    Agent --> Session
    Session --> Start["session.start(room, agent, room_io)"]
    Start --> Greet["generate_reply greeting (shared)"]

    Builder -->|"engine_mode = realtime"| RT["AgentSession(llm=RealtimeModel)"]
    Builder -->|"engine_mode = pipeline"| PL["AgentSession(stt, llm, tts, vad, turn_detection)"]
```

**Why tools are mode-agnostic:** tools attach to the LiveKit `Agent`
(`livekit_agent.update_tools(...)`), not to the model/session — so the existing
in-tree `BaseTool` registry, the MCP `RawFunctionTool` adapter, and the skills
`load_skill` tools all carry over to pipeline mode unchanged. (Bonus: the Gemini-realtime
schema-sanitization hack in `mcp/livekit_adapter.py` is only needed for the realtime
mode's strict validator; pipeline LLMs like OpenAI/Anthropic are more lenient.)

---

## 2. The two engine modes side by side

```mermaid
flowchart LR
    subgraph RT["Realtime mode (end-to-end, today)"]
        direction TB
        RUser["User audio"] --> RModel["Google RealtimeModel<br/>gemini-2.5-flash-native-audio"]
        RModel --> ROut["Audio out"]
        RModel -.-> RTools["function tools"]
    end
    subgraph PL["Pipeline mode (new)"]
        direction TB
        PUser["User audio"] --> VAD["VAD<br/>silero"]
        VAD --> STT["STT<br/>Deepgram (direct) / Inference (deepgram·assemblyai·…) / parakeet"]
        STT --> TD["Turn detector<br/>endpointing + barge-in"]
        TD --> LLM["LLM<br/>OpenAI (direct) / Cerebras (direct) / Inference (gemma·…) / Anthropic / Google"]
        LLM --> TTS["TTS<br/>Cartesia (direct) / Inference (cartesia·elevenlabs·…) / OpenAI"]
        TTS --> POut["Audio out (streamed chunks)"]
        LLM -.-> PTools["function tools + ChatContext"]
    end
```

Latency in pipeline mode comes from **streaming at every stage** (LiveKit already does
this): STT partials → LLM token stream → TTS first-chunk streaming, with VAD-driven
barge-in cancelling in-flight work. The HF repo's extra tricks we can layer on later
(see §6).

---

## 3. Provider factory abstraction (the modular core)

Borrowed from HF's `get_stt_handler` / `get_llm_handler` / `get_tts_handler` factory
pattern, but each builder returns a **LiveKit plugin instance** instead of a custom
handler. Each stage is independently swappable; adding a provider = one new builder
file + one factory branch + one config variant. No change to the session seam.

```mermaid
flowchart TD
    Cfg["SpeechConfig (per agent, from DB)"] --> Fac["stage factory"]
    Fac -->|"stt"| STTF["stt_factory.build(cfg.stt, keys)"]
    Fac -->|"llm"| LLMF["llm_factory.build(cfg.llm, keys)"]
    Fac -->|"tts"| TTSF["tts_factory.build(cfg.tts, keys)"]
    Fac -->|"vad"| VADF["vad_factory.build(cfg.vad)"]
    Fac -->|"turn_detection"| TDF["turn_detector_factory.build(cfg.turn_detection)"]
    Fac -->|"realtime"| RTF["realtime_factory.build(cfg.realtime, keys)"]

    STTF --> STTI["livekit.plugins.deepgram.STT / openai.STT / ..."]
    LLMF --> LLMI["livekit.plugins.openai.LLM / anthropic.LLM / google.LLM / ..."]
    TTSF --> TTSI["livekit.plugins.cartesia.TTS / elevenlabs.TTS / openai.TTS / ..."]
    VADF --> VADI["livekit.plugins.silero.VAD"]
    TDF --> TDI["livekit.plugins.turn_detector"]
    RTF --> RTI["livekit.plugins.google.realtime.RealtimeModel"]
```

---

## 4. Config data model (per-agent, modular, low schema churn)

A single JSONB column `speech_config` on `voice_agents`, validated by a **Pydantic
discriminated union**. JSONB avoids a migration every time we add a provider/field;
the discriminated union keeps it typed and validated. Backward-compatible default =
current realtime behavior, so existing agents are unaffected.

```mermaid
classDiagram
    class VoiceAgent {
        +existing fields
        +speech_config: JSONB  %% new
    }
    class SpeechConfig {
        +engine_mode: "realtime" | "pipeline"
    }
    class RealtimeConfig {
        +provider: "google"
        +model: string
        +voice: string
        +temperature: float
        +vad_endpointing: dict
    }
    class PipelineConfig {
        +stt: STTStageConfig
        +llm: LLMStageConfig
        +tts: TTSStageConfig
        +vad: VADConfig
        +turn_detection: TurnDetectionConfig
    }
    class STTStageConfig {
        +provider: "deepgram"|"openai"|"assemblyai"|...
        +model: string
        +language: string
        +params: dict
    }
    class LLMStageConfig {
        +provider: "openai"|"anthropic"|"google"|"groq"|"cerebras"|...
        +model: string
        +temperature: float
        +params: dict
    }
    class TTSStageConfig {
        +provider: "cartesia"|"elevenlabs"|"openai"|...
        +model: string
        +voice: string
        +params: dict
    }

    VoiceAgent --> SpeechConfig
    SpeechConfig <|-- RealtimeConfig : engine_mode=realtime
    SpeechConfig <|-- PipelineConfig : engine_mode=pipeline
    PipelineConfig --> STTStageConfig
    PipelineConfig --> LLMStageConfig
    PipelineConfig --> TTSStageConfig
```

---

## 5. API-key resolution (extended, shared) — ✅ Phase 3 done

Implemented in `shared/voice_agents/key_resolver.py` (`resolve_api_keys`).
All per-org provider keys live in **one Fernet-encrypted JSONB blob** on
`organizations.provider_credentials` (`encrypt_data`/`decrypt_data` in
`shared/common/security.py`), shape `{google, deepgram, openai, cartesia,
cerebras, livekit: {api_key, api_secret}}` (only the set keys present). This
consolidates the previously-plaintext `google_api_key` (a latent security gap)
and adds storage for the direct-provider + LiveKit Inference keys. The legacy
`google_api_key` column is retained but no longer the source of truth (dropped
in a follow-up migration).

The resolver pairs a `SpeechConfig` with the org's decrypted blob + the platform
env vars and returns a `{provider: api_key}` map, with the same org-vs-platform +
`use_platform_credits` semantics as before. **Only the providers the config
actually needs appear** in the result — a realtime agent gets just
`{"google": ...}`; an all-direct pipeline never touches `livekit`. Providers
with no resolvable key (neither org nor env) are **omitted** (no raise) — the
registry's existing per-provider guard raises a clear `ValueError` naming the
provider, preserving the current fail-fast behavior.

LiveKit **Inference** is the one special case: a single LiveKit Cloud auth
(`api_key` + `api_secret`) authenticates *all* Inference stages in a pipeline, so
the resolver injects it under a dedicated `livekit` entry (a nested
`{api_key, api_secret}` dict) **only when the preset's config actually contains a
stage with `provider == "livekit_inference"`** — not one key per Inference stage.
Rationale: the platform's LiveKit plan limits won't scale to all tenants' calls,
so a tenant can bring its own LiveKit key for **Inference only**; a future path
migrates LiveKit rooms/sessions to tenant keys. Direct providers
(Deepgram/OpenAI/Cartesia/Cerebras) each keep their own per-org / platform key.
The registry's `_build_livekit_inference_stage` reads `api_keys["livekit"]` and
passes `api_key`/`api_secret` to the Inference builders (falling back to env when
both are `None`).

```mermaid
flowchart TD
    Agent["VoiceAgent.preset_id -> preset.config (SpeechConfig)"] --> Resolver["key_resolver.resolve_api_keys(speech_config, org, use_platform_credits)"]
    Blob["organizations.provider_credentials (encrypted JSONB)"] -->|decrypt_data| Resolver
    Plat["platform env: GEMINI/OPENAI/DEEPGRAM/CARTESIA/CEREBRAS_API_KEY, LIVEKIT_API_KEY/SECRET"] --> Resolver
    Credits["agent.use_platform_credits"] --> Resolver
    Resolver --> Map["{google|openai|deepgram|cartesia|cerebras: str, livekit: {api_key, api_secret} (only when an Inference stage is used)}"]
    Map --> Factories["registry.build_session_components (inference stages read livekit; direct stages read their own)"]
```

---

## 6. Latency techniques — what LiveKit gives us vs. what we borrow from HF

```mermaid
flowchart LR
    subgraph LK["LiveKit pipeline mode gives us (free)"]
        L1["Streaming STT partials"]
        L2["LLM token streaming"]
        L3["TTS first-chunk streaming"]
        L4["VAD-driven barge-in / interruption"]
        L5["Silero VAD + turn detector"]
    end
    subgraph Borrow["Borrow from HF speech-to-speech (later, optional)"]
        B1["SpeculativeTurnTracker<br/>start turn on raw audio, reopen if superseded"]
        B2["CancelScope generation counter<br/>atomic cross-stage stale-drop"]
        B3["Sentence-batched LLM→TTS handoff<br/>faster time-to-first-audio"]
        B4["TTS leading-silence trim"]
        B5["Background ChatContext compaction<br/>long conversations"]
        B6["Model warmup at worker boot<br/>avoid cold-start first turn"]
    end
    LK --> MVP["MVP: native pipeline mode"]
    Borrow --> V2["v2: latency hardening"]
```

MVP = native LiveKit pipeline mode + provider factories + config + key resolution.
The HF-style speculative-turn / cancel-scope / compaction work is **v2 latency
hardening**, not a blocker for the core capability.

---

## 7. Component layout (worker + shared)

```mermaid
flowchart TD
    subgraph shared["shared/voice_agents/"]
        M["models.py  (+speech_config field)"]
        PB["prompt_builder.py (unchanged)"]
        Svc["service.py (fetch + speech_config hydration)"]
    end
    subgraph worker["worker/src/"]
        W["worker.py (entrypoint, calls session_builder)"]
        SB["session_builder.py  (THE SEAM, new)"]
        SP["speech_providers/  (new package)"]
        SP --> RTp["realtime/ (refactored from realtime_config.py)"]
        SP --> STTp["stt/ factory + builders"]
        SP --> LLMp["llm/ factory + builders"]
        SP --> TTSp["tts/ factory + builders"]
        SP --> VADp["vad/ factory"]
        SP --> TDp["turn_detection/ factory"]
        KR["key_resolver.py  (new, extends existing key logic)"]
    end
    subgraph backend["backend/ (config CRUD)"]
        Routes["API routes for speech_config"]
        Migration["alembic migration: add voice_agents.speech_config"]
    end
    subgraph frontend["frontend/ (later)"]
        UI["Agent voice-engine config UI"]
    end
    W --> SB --> SP
    W --> KR
    Svc --> M
```

---

## 8. Phased rollout

```mermaid
flowchart TD
    P1["Phase 1 — Foundation (no behavior change)"]:::p1 --> P2["Phase 2 — Pipeline engine"]:::p2 --> P3["Phase 3 — Config & keys"]:::p3 --> P4["Phase 4 — UI & RBAC gating"]:::p4 --> P5["Phase 5 — Latency hardening (v2)"]:::p5
    classDef p1 fill:#e8f5e9,stroke:#2e7d32;
    classDef p2 fill:#e3f2fd,stroke:#1565c0;
    classDef p3 fill:#fff3e0,stroke:#ef6c00;
    classDef p4 fill:#f3e5f5,stroke:#6a1b9a;
    classDef p5 fill:#fce4ec,stroke:#ad1457;
```

- **P1 Foundation:** Extract `session_builder` + `speech_providers/` package; refactor
  existing `realtime_config.py` into the `realtime/` provider behind the factory.
  Net behavior identical. Existing realtime tests stay green. (Pure refactor — the
  seam now exists but only realtime is wired.) **✅ Done** — config models in
  `shared/voice_agents/speech_config.py`, provider package in
  `worker/src/speech_providers/`, seam in `worker/src/session_builder.py`, worker
  wired through, 100% coverage on new modules.
- **P2 Pipeline engine:** Add `stt/`, `llm/`, `tts/`, `vad/`, `turn_detection/`
  factories + ≥1 provider each (e.g. Deepgram STT, OpenAI LLM, Cartesia TTS, Silero
  VAD). `session_builder` branches on `engine_mode`. Install the LiveKit plugin
  packages. Unit + integration tests with mocked plugins. **✅ Done** — per-stage
  builders in `worker/src/speech_providers/{stt,llm,tts,vad}/`
  (Deepgram `nova-3`, OpenAI `gpt-4.1`, Cartesia `sonic-3`, Silero VAD via the
  offline `VAD.load` classmethod), table-driven dispatch + per-provider key
  guards in `registry.py`, conditional `vad`/`turn_detection` assembly in
  `session_builder.py`, env scaffolding (`DEEPGRAM_API_KEY` / `OPENAI_API_KEY` /
  `CARTESIA_API_KEY` in `.env.example` + `docker-compose.dev.yml`). The registry
  always builds an explicit standalone Silero VAD for the pipeline (even when
  `config.vad` is `None`) to keep it off the bundled `livekit.agents.inference`
  VAD / missing-Pillow path (deferred bug #7). `turn_detection` is deferred to
  Phase 5 (non-`None` config raises `NotImplementedError`). 100% coverage on the
  new modules; behavior-neutral (worker still uses the realtime default).
- **P2b Inference + Cerebras:** Add LiveKit **Inference** as a dispatchable
  provider for STT/LLM/TTS (single LiveKit Cloud auth via `api_key`+`api_secret`,
  special dispatch path in `registry.py` bypassing the per-provider key guard)
  and **Cerebras** as a direct LLM (`openai.LLM.with_cerebras`, keyed path). A
  pipeline may mix Inference and direct stages per stage (the "mixed preset"
  direction — still just a pipeline). **✅ Done** —
  `worker/src/speech_providers/{stt,llm,tts}/livekit_inference.py` +
  `worker/src/speech_providers/llm/cerebras.py`; Inference reads the platform
  LiveKit key from the env (Phase 2b), with `api_key`/`api_secret` builder kwargs
  as the Phase 3 per-org injection seam; Inference has no implicit default model
  (raises `ValueError`) and splits `params` into top-level kwargs vs
  `extra_kwargs` (LLM `temperature`, STT `keywords`, etc. are not top-level).
  100% coverage on the new modules; behavior-neutral (worker still uses the
  realtime default).
- **P3 Presets, config & keys:** Platform-admin-managed **pipeline presets**
  (Alembic migration `20260729000001` adding the `pipeline_presets` catalog table +
  `voice_agents.preset_id` FK + `organizations.provider_credentials` encrypted blob).
  Two preset types only — `{realtime, pipeline}`; a "mixed" preset is just a
  pipeline mixing Inference + direct stages. **No versioning (locked decision):**
  the agent stores only `preset_id`; the worker fetches the preset row **live on
  every call** (`preset_service.get_preset_by_id`), so an admin's edit takes effect
  on the next call — no `preset_version`, no snapshot. Pydantic discriminated-union
  validation (`shared/voice_agents/preset_models.py`); `preset_type` is derived from
  `config.engine_mode` on every write (denormalized filter column, never hand-set).
  Per-provider **key resolver** (`shared/voice_agents/key_resolver.py`): reads all
  keys from the decrypted `provider_credentials` blob (not the plaintext
  `google_api_key` column), injects `livekit: {api_key, api_secret}` **only when an
  Inference stage is used**, omits providers with no resolvable key. Backend CRUD +
  RBAC (`backend/src/voice_agents/preset_routes.py`, platform_admin) + agent
  assignment validation (must exist + be published) + org-credential write/read
  (encrypt into the blob, clear the plaintext column). 100% coverage on
  `key_resolver`/`preset_models`/`preset_service`; no frontend in this phase (no
  browser validation). **✅ Done.** Migration reviewed but **not run** — awaits
  owner approval (`alembic upgrade head` in the backend container).
- **P4 UI & RBAC:** Frontend preset picker + platform-admin preset management UI +
  per-provider org-credentials UI (fold `engine_mode` into one "voice profile"
  picker; user never sees engine mode / STT/LLM/TTS). RBAC gating on who can switch
  engines/configure stages (deferred decision — wiring point only). E2E + browser
  validation.
- **P5 Latency hardening (v2):** SpeculativeTurnTracker, CancelScope cross-stage stale
  drop, sentence-batched LLM→TTS, TTS leading-silence trim, ChatContext compaction,
  model warmup. Benchmarks before/after.

---

## 9. Testing & documentation strategy

- **Unit:** provider factories (assert correct LiveKit plugin + params from a config),
  Pydantic discriminated-union validation (valid/invalid/defaults), key resolver
  (org vs platform vs `use_platform_credits`), `session_builder` branching
  (realtime vs pipeline construction).
- **Integration:** pipeline-mode session start with mocked plugins; tool/MCP invocation
  in pipeline mode (verifies the mode-agnostic tool claim); barge-in cancellation.
- **Regression:** existing realtime tests stay green throughout (P1 is behavior-neutral).
- **Docs:** this file (architecture), a `voice_engine.md` module doc, provider-plugin
  guide (`docs/03_development/`), `DATABASE_SCHEMA.md` update for `speech_config`,
  README updates for `worker/` and `shared/`.
- **Validation gates (per CLAUDE.md):** `py_compile` on changed files, `pytest` with
  coverage of new branches, `agent-browser` smoke test of the config UI, cleanup of
  smoke artifacts. No git commits without explicit approval.