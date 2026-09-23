import { describe, expect, it } from "vitest";
import {
  buildProviderCredentialDescriptionsInput,
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
  resend: "",
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

  it("sets a touched Resend key for organization email tools", () => {
    expect(
      buildProviderCredentialsInput(
        { ...emptyDraft, resend: " re_org_key " },
        { resend: true },
      ),
    ).toEqual({ resend: "re_org_key" });
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

  it("counts a provider touched only through its description once", () => {
    expect(
      countPendingProviderCredentialChanges(
        { openai: false },
        { openai: true, deepgram: true },
      ),
    ).toBe(2);
  });
});

describe("buildProviderCredentialDescriptionsInput", () => {
  it("trims and sends only touched notes", () => {
    expect(
      buildProviderCredentialDescriptionsInput(
        { openai: " Production key ", deepgram: "ignored" },
        { openai: true },
      ),
    ).toEqual({ openai: "Production key" });
  });

  it("clears a touched note when the draft is empty", () => {
    expect(
      buildProviderCredentialDescriptionsInput(
        { openrouter: "   " },
        { openrouter: true },
      ),
    ).toEqual({ openrouter: null });
  });
});
