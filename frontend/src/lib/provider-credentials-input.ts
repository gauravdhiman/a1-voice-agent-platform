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
] as const;

export type SimpleProviderKey = (typeof SIMPLE_PROVIDER_KEYS)[number];

export type ProviderCredentialKey = SimpleProviderKey | "livekit";

export const PROVIDER_LABELS: Record<ProviderCredentialKey, string> = {
  google: "Google",
  deepgram: "Deepgram",
  openai: "OpenAI",
  cartesia: "Cartesia",
  cerebras: "Cerebras",
  openrouter: "OpenRouter",
  fish: "Fish Audio",
  livekit: "LiveKit",
};

export interface ProviderCredsDraft {
  google: string;
  deepgram: string;
  openai: string;
  cartesia: string;
  cerebras: string;
  openrouter: string;
  fish: string;
  livekit_api_key: string;
  livekit_api_secret: string;
}

export type ProviderCredentialsInput = Record<
  string,
  string | { api_key: string; api_secret: string } | null
>;

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

  if (touched.livekit) {
    const apiKey = draft.livekit_api_key.trim();
    const apiSecret = draft.livekit_api_secret.trim();
    input.livekit =
      apiKey || apiSecret ? { api_key: apiKey, api_secret: apiSecret } : null;
  }

  return input;
}

/**
 * Count how many providers have unsaved draft changes.
 */
export function countPendingProviderCredentialChanges(
  touched: Record<string, boolean>,
): number {
  return Object.values(touched).filter(Boolean).length;
}
