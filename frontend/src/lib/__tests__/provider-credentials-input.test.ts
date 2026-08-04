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
  openrouter: "",
  fish: "",
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
});

describe("countPendingProviderCredentialChanges", () => {
  it("counts touched providers", () => {
    expect(
      countPendingProviderCredentialChanges({
        google: true,
        deepgram: false,
        openrouter: true,
      }),
    ).toBe(2);
  });
});
