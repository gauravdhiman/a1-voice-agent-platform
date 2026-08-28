/**
 * Types for the unauthenticated public organization showcase page.
 */

export interface PublicOrgSummary {
  id: string;
  name: string;
  description: string | null;
  slug: string;
  passphrase_required: boolean;
}

export interface PublicAgentSummary {
  id: string;
  name: string;
  persona: string | null;
  mission: string | null;
  is_demo: boolean;
  demo_calls_remaining: number | null;
  demo_max_call_duration_seconds: number | null;
}

export interface PublicOrgAgentsResponse {
  agents: PublicAgentSummary[];
}

export interface PublicCallTokenResponse {
  token: string;
  wsUrl: string;
  sessionId: string;
  demo_calls_remaining?: number | null;
  demo_max_call_duration_seconds?: number | null;
}
