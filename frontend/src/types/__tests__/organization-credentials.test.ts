/**
 * Type-level + runtime tests for the Phase 4 provider-credentials fields on the
 * organization interfaces.
 *
 * Contract:
 *  - `Organization` (read) carries `provider_credentials_status` — a per-
 *    provider boolean map (google/deepgram/openai/cartesia/cerebras/openrouter/fish/livekit),
 *    never the decrypted values.
 *  - `OrganizationUpdate` (write) carries `provider_credentials_input` —
 *    touched providers only; a string to set, `null` to clear, `{api_key,
 *    api_secret}` for livekit.
 */
import { describe, it, expect, expectTypeOf } from "vitest";

import type { Organization, OrganizationUpdate } from "@/types/organization";

describe("Organization provider_credentials_status (read)", () => {
  it("Organization exposes provider_credentials_status as an optional boolean map", () => {
    expectTypeOf<Organization>()
      .toHaveProperty("provider_credentials_status")
      .toMatchTypeOf<Record<string, boolean> | undefined>();
  });

  it("a fully-formed status map round-trips through the interface", () => {
    const org: Organization = {
      id: "o1",
      name: "Acme",
      description: null,
      slug: "acme",
      website: null,
      is_active: true,
      onboarding_completed: true,
      created_at: "2026-07-29T00:00:00Z",
      updated_at: "2026-07-29T00:00:00Z",
      provider_credentials_status: {
        google: true,
        deepgram: false,
        openai: true,
        cartesia: false,
        cerebras: false,
        openrouter: false,
        fish: false,
        livekit: true,
      },
    };
    expect(org.provider_credentials_status?.google).toBe(true);
    expect(org.provider_credentials_status?.deepgram).toBe(false);
    expect(org.provider_credentials_status?.openrouter).toBe(false);
    expect(org.provider_credentials_status?.fish).toBe(false);
    expect(org.provider_credentials_status?.livekit).toBe(true);
  });
});

describe("OrganizationUpdate provider_credentials_input (write)", () => {
  it("OrganizationUpdate exposes provider_credentials_input as optional", () => {
    expectTypeOf<OrganizationUpdate>()
      .toHaveProperty("provider_credentials_input")
      .toMatchTypeOf<
        | Record<
            string,
            string | { api_key: string; api_secret: string } | null
          >
        | undefined
      >();
  });

  it("can set a simple provider with a string", () => {
    const update: OrganizationUpdate = {
      provider_credentials_input: { deepgram: "dg-key" },
    };
    expect(update.provider_credentials_input?.deepgram).toBe("dg-key");
  });

  it("can clear a provider with null", () => {
    const update: OrganizationUpdate = {
      provider_credentials_input: { openai: null },
    };
    expect(update.provider_credentials_input?.openai).toBeNull();
  });

  it("can set livekit with {api_key, api_secret}", () => {
    const update: OrganizationUpdate = {
      provider_credentials_input: {
        livekit: { api_key: "lk-key", api_secret: "lk-secret" },
      },
    };
    expect(update.provider_credentials_input?.livekit).toEqual({
      api_key: "lk-key",
      api_secret: "lk-secret",
    });
  });
});