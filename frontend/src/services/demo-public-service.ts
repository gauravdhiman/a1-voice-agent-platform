/**
 * Client for unauthenticated public demo-agent page APIs.
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface DemoAgentPublic {
  /** Stable agent identifier returned to the public page. */
  id: string;
  /** Visitor-facing agent name. */
  name: string;
  /** Unique public demo slug. */
  demo_slug: string;
  /** Optional runtime persona metadata. */
  persona: string | null;
  /** Optional runtime mission metadata. */
  mission: string | null;
  /** Optional runtime tone metadata. */
  tone: string | null;
  /** Optional visitor-facing marketing copy. */
  public_description: string | null;
  /** Owning organization identifier. */
  organization_id: string;
  /** Optional owning organization name for display. */
  organization_name: string | null;
  /** Remaining trial calls; zero disables new calls and -1 is unlimited. */
  demo_calls_remaining: number;
  /** Maximum duration in seconds; -1 is unlimited. */
  demo_max_call_duration_seconds: number;
}

export interface DemoCallTokenResponse {
  /** Short-lived JWT accepted by the Pipecat voice worker. */
  token: string;
  /** WebSocket endpoint selected by the backend. */
  wsUrl: string;
  /** Session identifier used for voice-session tracking. */
  sessionId: string;
  /** Remaining trial calls after this token was reserved. */
  demo_calls_remaining?: number | null;
  /** Duration cap captured for this call; -1 means unlimited. */
  demo_max_call_duration_seconds?: number | null;
}

/**
 * Service for the unauthenticated demo-agent page.
 *
 * Demo metadata and call-token endpoints deliberately contain no dashboard
 * credentials. The backend remains responsible for checking that the slug
 * belongs to an active demo agent and for applying the demo billing policy.
 */
class DemoPublicService {
  /**
   * Fetches safe metadata for an active demo agent.
   *
   * @param slug - Public demo slug from the `/demo/{slug}` route.
   * @returns Promise resolving to visitor-safe demo metadata.
   * @throws {Error} When the slug is missing, inactive, or not a demo agent.
   */
  async getDemoAgent(slug: string): Promise<DemoAgentPublic> {
    const res = await fetch(
      `${API_BASE_URL}/api/v1/public/demo/${encodeURIComponent(slug)}`,
      { cache: "no-store" }
    );
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail || "Demo agent not found");
    }
    return (await res.json()) as DemoAgentPublic;
  }

  /**
   * Requests a short-lived Pipecat voice-session token for a demo visitor.
   *
   * @param slug - Public demo slug from the current page.
   * @returns Promise resolving to the voice token, WebSocket URL, and session ID.
   * @throws {Error} When the backend cannot admit or initialize the call.
   */
  async getCallToken(slug: string): Promise<DemoCallTokenResponse> {
    const res = await fetch(
      `${API_BASE_URL}/api/v1/public/demo/${encodeURIComponent(slug)}/call-token`,
      { method: "POST", headers: { "Content-Type": "application/json" } }
    );
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      const detail = body.detail;
      const message =
        typeof detail === "object" && detail?.message
          ? detail.message
          : typeof detail === "string"
            ? detail
            : "Failed to start call";
      throw new Error(message);
    }
    return (await res.json()) as DemoCallTokenResponse;
  }
}

export const demoPublicService = new DemoPublicService();
