/**
 * Type-level + runtime tests for the `preset_id` field on the voice-agent
 * interfaces (Phase 4).
 *
 * Contract: the backend `VoiceAgent` response (`shared/voice_agents/models.py`)
 * carries `preset_id` (FK to `pipeline_presets.id`, NULL = realtime default),
 * and the create/update models accept it. The frontend must surface it so the
 * agent picker can prefill + clear the assignment. These tests pin the presence
 * and shape of `preset_id` on `VoiceAgent` / `VoiceAgentCreate` /
 * `VoiceAgentUpdate`.
 */
import { describe, it, expect, expectTypeOf } from "vitest";

import type {
  VoiceAgent,
  VoiceAgentCreate,
  VoiceAgentUpdate,
} from "@/types/agent";

describe("VoiceAgent preset_id field", () => {
  it("VoiceAgent exposes preset_id as string | null", () => {
    expectTypeOf<VoiceAgent>()
      .toHaveProperty("preset_id")
      .toMatchTypeOf<string | null>();
  });

  it("VoiceAgentCreate accepts preset_id as optional string | null", () => {
    expectTypeOf<VoiceAgentCreate>()
      .toHaveProperty("preset_id")
      .toMatchTypeOf<string | null | undefined>();
  });

  it("VoiceAgentUpdate accepts preset_id as optional string | null", () => {
    expectTypeOf<VoiceAgentUpdate>()
      .toHaveProperty("preset_id")
      .toMatchTypeOf<string | null | undefined>();
  });

  it("a fully-formed agent with a preset round-trips through the interface", () => {
    const agent: VoiceAgent = {
      id: "a1",
      organization_id: "o1",
      name: "Support Agent",
      description: null,
      phone_number: "+14155551234",
      system_prompt: null,
      persona: "Front Desk",
      tone: "Professional",
      mission: "Book appointments",
      custom_instructions: null,
      voice_settings: null,
      is_active: true,
      use_platform_credits: false,
      instructions_markdown: null,
      preset_id: "p-1",
      created_by: "u1",
      created_at: "2026-07-29T00:00:00Z",
      updated_at: "2026-07-29T00:00:00Z",
    };
    expect(agent.preset_id).toBe("p-1");
  });

  it("an agent with no preset carries preset_id = null (realtime default)", () => {
    const agent: VoiceAgent = {
      id: "a2",
      organization_id: "o1",
      name: "Legacy Agent",
      description: null,
      phone_number: null,
      system_prompt: null,
      persona: null,
      tone: null,
      mission: null,
      custom_instructions: null,
      voice_settings: null,
      is_active: true,
      use_platform_credits: false,
      instructions_markdown: null,
      preset_id: null,
      created_by: "u1",
      created_at: "2026-07-29T00:00:00Z",
      updated_at: "2026-07-29T00:00:00Z",
    };
    expect(agent.preset_id).toBeNull();
  });

  it("a create payload can clear a preset by sending preset_id = null", () => {
    const payload: VoiceAgentCreate = {
      organization_id: "o1",
      name: "Agent",
      preset_id: null,
    };
    expect(payload.preset_id).toBeNull();
  });

  it("an update payload can clear a preset by sending preset_id = null", () => {
    const payload: VoiceAgentUpdate = { preset_id: null };
    expect(payload.preset_id).toBeNull();
  });
});