/**
 * Helpers for building `provider_credentials_input` payloads sent to the
 * organization update API. Only touched keys are included so unchanged
 * credentials are preserved server-side.
 */

export const SIMPLE_PROVIDER_KEYS = [
  "google",
  "deepgram",
  "openai",
  "cartesia",
  "cerebras",
  "openrouter",
  "fish",
  "resend",
] as const;

export type SimpleProviderKey = (typeof SIMPLE_PROVIDER_KEYS)[number];

export interface ProviderCredentialDefinition {
  label: string;
  setupUrl: string;
  helpText: string;
}

/** Provider-specific guidance shown beside each write-only API key field. */
export const PROVIDER_DEFINITIONS: Record<
  SimpleProviderKey,
  ProviderCredentialDefinition
> = {
  google: {
    label: "Google",
    setupUrl: "https://aistudio.google.com/apikey",
    helpText:
      "A Google Gemini API key for Google voice models. Create or manage keys in Google AI Studio.",
  },
  deepgram: {
    label: "Deepgram",
    setupUrl: "https://console.deepgram.com/",
    helpText:
      "A Deepgram project API key for speech-to-text. Use a key with the scopes required by your voice setup.",
  },
  openai: {
    label: "OpenAI",
    setupUrl: "https://platform.openai.com/api-keys",
    helpText:
      "An OpenAI API key for OpenAI speech or language models. Keep usage limits and billing settings in mind.",
  },
  cartesia: {
    label: "Cartesia",
    setupUrl: "https://play.cartesia.ai/",
    helpText:
      "A Cartesia API key for Cartesia text-to-speech voices.",
  },
  cerebras: {
    label: "Cerebras",
    setupUrl: "https://cloud.cerebras.ai/platform",
    helpText:
      "A Cerebras API key for Cerebras language models.",
  },
  openrouter: {
    label: "OpenRouter",
    setupUrl: "https://openrouter.ai/settings/keys",
    helpText:
      "An OpenRouter API key for routing language-model requests through OpenRouter.",
  },
  fish: {
    label: "Fish Audio",
    setupUrl: "https://fish.audio/go-api/",
    helpText:
      "A Fish Audio API key for Fish Audio text-to-speech voices.",
  },
  resend: {
    label: "Resend",
    setupUrl: "https://resend.com/api-keys",
    helpText:
      "A Resend API key for organization email delivery tools.",
  },
};

export type ProviderCredentialKey = SimpleProviderKey;

export const PROVIDER_LABELS: Record<ProviderCredentialKey, string> = {
  google: PROVIDER_DEFINITIONS.google.label,
  deepgram: PROVIDER_DEFINITIONS.deepgram.label,
  openai: PROVIDER_DEFINITIONS.openai.label,
  cartesia: PROVIDER_DEFINITIONS.cartesia.label,
  cerebras: PROVIDER_DEFINITIONS.cerebras.label,
  openrouter: PROVIDER_DEFINITIONS.openrouter.label,
  fish: PROVIDER_DEFINITIONS.fish.label,
  resend: PROVIDER_DEFINITIONS.resend.label,
};

export interface ProviderCredsDraft {
  google: string;
  deepgram: string;
  openai: string;
  cartesia: string;
  cerebras: string;
  openrouter: string;
  fish: string;
  resend: string;
}

export type ProviderCredentialsInput = Record<string, string | null>;
export type ProviderCredentialDescriptions = Partial<
  Record<SimpleProviderKey, string>
>;
export type ProviderCredentialDescriptionsInput = Record<string, string | null>;

/**
 * Build the API payload from draft values and touched flags.
 *
 * Non-empty touched values SET a key; empty touched values CLEAR it (`null`).
 * Untouched keys are omitted so the backend preserves existing secrets.
 */
export function buildProviderCredentialsInput(
  draft: ProviderCredsDraft,
  touched: Record<string, boolean>,
): ProviderCredentialsInput {
  const input: ProviderCredentialsInput = {};

  for (const key of SIMPLE_PROVIDER_KEYS) {
    if (touched[key]) {
      const val = draft[key].trim();
      input[key] = val ? val : null;
    }
  }

  return input;
}

/**
 * Count how many providers have unsaved draft changes.
 */
export function countPendingProviderCredentialChanges(
  touched: Record<string, boolean>,
  additionalTouched: Record<string, boolean> = {},
): number {
  const keys = new Set([...Object.keys(touched), ...Object.keys(additionalTouched)]);
  return [...keys].filter((key) => touched[key] || additionalTouched[key]).length;
}

/**
 * Build the API payload for non-secret provider reference notes.
 *
 * Empty touched values clear a note (`null`); untouched providers are omitted.
 */
export function buildProviderCredentialDescriptionsInput(
  descriptions: ProviderCredentialDescriptions,
  touched: Record<string, boolean>,
): ProviderCredentialDescriptionsInput {
  const input: ProviderCredentialDescriptionsInput = {};

  for (const key of SIMPLE_PROVIDER_KEYS) {
    if (touched[key]) {
      const value = descriptions[key]?.trim() ?? "";
      input[key] = value ? value : null;
    }
  }

  return input;
}
