/**
 * Voice template type definitions for the onboarding wizard.
 */

export interface VoiceTemplate {
  id: string;
  name: string;
  industry: string;
  description: string | null;
  persona: string | null;
  tone: string | null;
  mission: string | null;
  greeting: string | null;
  custom_instructions: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}
