/** Secret-free platform voice-provider credential status returned to admins. */
export type VoiceProviderKey =
  | "google"
  | "deepgram"
  | "openai"
  | "cartesia"
  | "cerebras"
  | "openrouter"
  | "fish";

export interface PlatformVoiceProviderCredentialStatus {
  configured: boolean;
  environment_fallback_configured: boolean;
  updated_at?: string | null;
}

export interface PlatformVoiceProviderCredentialsResponse {
  providers: Record<VoiceProviderKey, PlatformVoiceProviderCredentialStatus>;
}
