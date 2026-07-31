import { describe, expect, it } from "vitest";
import {
  buildProviderCredentialsInput,
  countPendingProviderCredentialChanges,
} from "@/lib/provider-credentials-input";

const emptyDraft = {
  google: "",
  deepgram: "",
  openai: "",
  cartesia: "",
  cerebras: "",
  livekit_api_key: "",
  livekit_api_secret: "",
};

describe("buildProviderCredentialsInput", () => {
  it("omits untouched providers", () => {
    expect(
      buildProviderCredentialsInput(
        { ...emptyDraft, deepgram: "dg-key" },
        {},
      ),
    ).toEqual({});
  });

  it("sets a non-empty touched simple key", () => {
    expect(
      buildProviderCredentialsInput(
        { ...emptyDraft, openai: " sk-key " },
        { openai: true },
      ),
    ).toEqual({ openai: "sk-key" });
  });

  it("clears a touched simple key when the draft is empty", () => {
    expect(
      buildProviderCredentialsInput(
        { ...emptyDraft, cartesia: "" },
        { cartesia: true },
      ),
    ).toEqual({ cartesia: null });
  });

  it("sets LiveKit when either field has a value", () => {
    expect(
      buildProviderCredentialsInput(
        {
          ...emptyDraft,
          livekit_api_key: "lk-key",
          livekit_api_secret: "",
        },
        { livekit: true },
      ),
    ).toEqual({ livekit: { api_key: "lk-key", api_secret: "" } });
  });

  it("clears LiveKit when both touched fields are empty", () => {
    expect(
      buildProviderCredentialsInput(
        { ...emptyDraft, livekit_api_key: "", livekit_api_secret: "" },
        { livekit: true },
      ),
    ).toEqual({ livekit: null });
  });
});

describe("countPendingProviderCredentialChanges", () => {
  it("counts touched providers", () => {
    expect(
      countPendingProviderCredentialChanges({
        google: true,
        deepgram: false,
        livekit: true,
      }),
    ).toBe(2);
  });
});
