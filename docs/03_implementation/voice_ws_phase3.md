# Voice WebSocket Phase 3: parity modules

**Status:** Implemented  
**ADR:** [Pipecat transport](../01_architecture/ADR_VOICE_WS_PIPECAT.md)

Phase 3 brings the active `voice-ws` transport to functional parity for
agent-defined speech presets, legacy tools, MCP tools, and progressively
disclosed skills.

## Runtime flow

```mermaid
flowchart LR
  JWT[Verified session JWT] --> Setup[prepare_voice_session]
  Setup --> Prompt[Prompt + tools + skills]
  Setup --> Realtime[Gemini Live]
  Setup --> Pipeline[Deepgram → OpenAI/Cerebras/OpenRouter → Cartesia/Fish]
  Prompt --> Realtime
  Prompt --> Pipeline
```

## Prompt and tool contract boundary

The model context has three deliberately separate sources:

- `PromptBuilder` combines platform guardrails, organization context, agent
  instructions, assigned skill summaries, and the runtime date/time anchor. It
  does not receive attached tool names and must remain valid for any agent.
- `DEFAULT_VOICE_SYSTEM_PROMPT` contains generic tool-use, error-handling, and
  anti-hallucination behavior. Organization and agent instructions may add
  business-specific or tool-specific guidance when configured by the user.
- Native function schemas are generated from native method docstrings, while
  MCP function schemas use the descriptions returned by `tools/list`. These
  schemas are passed through the model's tool-definition channel rather than
  copied into the generic platform prompt. The schema is the source of truth for
  a tool's purpose, arguments, constraints, and result contract.

Tool load failures remain in `unavailable_tools` for logs and diagnostics. They
are not rendered into the model context because exposing internal connector
names or failure details is both unnecessary and another source of prompt drift.

- `src/tools/assembly.py` discovers shared `BaseTool` implementations, injects
  `ToolContext`, and preserves function-level enablement. Failed MCP/legacy
  tools are recorded as `unavailable_tools` for logs and diagnostics only; they
  are not copied into the platform prompt. Available native function schemas and
  MCP `tools/list` descriptions remain the model-facing source of tool guidance.
- `src/tools/mcp_pipecat.py` discovers remote MCP schemas, sanitizes Gemini
  schemas, and owns MCP client lifecycle through call teardown.
- Skills expose `load_skill` and `load_skill_reference` only when assigned.
- `src/speech/factory.py` supports Gemini Live and direct Deepgram STT,
  OpenAI / Cerebras / OpenRouter LLM, Cartesia / Fish Audio TTS, and Silero VAD.
  For OpenRouter, reasoning is disabled by default via `extra_body.reasoning`
  (`effort=none`, `exclude=true`) so Gemma-style thinking channels do not stream
  into assistant content. Pipeline Cartesia/Fish TTS also attach
  `ThinkingChannelTextFilter` to strip any leaked `<|channel>…` / `<think>`
  markers before synthesis.
- Dev compose runs `voice-ws/entrypoint.dev.sh`, which co-starts the local
  Google Calendar REST MCP connector on `127.0.0.1:8733` (required for
  `Google_calendar_mcp`).

Pipeline presets must use **direct** providers only (`deepgram`, `openai`,
`cerebras`, `openrouter`, `cartesia`, `fish`, etc.). Legacy
Deprecated preset provider slug **`livekit_inference`** (removed provider name, not
the LiveKit product) stages were removed; migration
`20260803000001_remove_livekit_inference_from_presets` rewrites any remaining
DB rows to direct providers. An unmappable pipeline stage (or missing
direct-provider key) logs an error and falls back to the Gemini realtime default
so the call still connects.

## How to test

1. **Realtime + tools:** Assign Gmail/Calendar (or MCP) tools + a skill to an
   agent on a Gemini realtime preset. Web test call and phone call should greet,
   then execute tools / `load_skill` when asked.
2. **Pipeline preset:** Point the agent at a Deepgram → OpenRouter → Fish (or
   OpenAI/Cerebras → Cartesia) preset with **direct** providers. Confirm
   STT/LLM/TTS path speaks and tools still work.
3. Env: same as Phase 2, plus pipeline keys as needed
   (`DEEPGRAM_API_KEY`, `OPENAI_API_KEY` / `CEREBRAS_API_KEY` /
   `OPENROUTER_API_KEY`, `CARTESIA_API_KEY` / `FISH_API_KEY`).
   For Fish TTS, set the preset **voice** field to a Fish Audio voice
   `reference_id` (model e.g. `s2.1-pro-free`).
