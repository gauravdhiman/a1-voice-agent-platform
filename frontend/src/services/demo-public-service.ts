/**
 * Client for unauthenticated public demo-agent page APIs.
 */

import { getCurrentPageSourceUrl } from "@/lib/source-url";

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
  /** Signed token that authorizes the visitor's private outcome receipt. */
  receiptToken: string;
  /** Remaining trial calls after this token was reserved. */
  demo_calls_remaining?: number | null;
  /** Duration cap captured for this call; -1 means unlimited. */
  demo_max_call_duration_seconds?: number | null;
}

export type DemoOutcomeActionType =
  "lead_capture" | "appointment_booking" | "email_delivery";
export type DemoOutcomeActionStatus = "succeeded" | "failed" | "pending";

export interface DemoOutcomeProviderResult {
  record_type?: string | null;
  record_id?: string | null;
  /** Provider-generated link, present only when it is safe to expose. */
  record_url?: string | null;
  record_status?: string | null;
  note_id?: string | null;
  start_time?: string | null;
  end_time?: string | null;
  message?: string | null;
  [key: string]: unknown;
}

export interface DemoOutcomeAction {
  /** Receipt row identifier. */
  id: string;
  /** Visitor-facing workflow label. */
  action_type: DemoOutcomeActionType;
  /** Provider that received the mutation. */
  provider: string;
  /** Whether the provider mutation succeeded, failed, or still needs action. */
  status: DemoOutcomeActionStatus;
  /** Platform-admin-configured public destination, present only after success. */
  public_result_url?: string | null;
  /** Stable safe error code, when the provider did not complete. */
  error_code: string | null;
  /** Confirmed fields captured during the call. */
  captured_fields: Record<string, string | number | boolean | null>;
  /** Safe provider identifiers and delivery summary. */
  provider_result: DemoOutcomeProviderResult;
  /** Receipt creation time. */
  created_at: string;
  /** Receipt expiry time. */
  expires_at: string;
}

export interface DemoOutcome {
  demo_slug: string;
  agent_name: string;
  organization_name: string | null;
  status: "completed" | "needs_attention" | "no_action";
  actions: DemoOutcomeAction[];
  expires_at: string | null;
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
      { cache: "no-store" },
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
    const pageSourceUrl = getCurrentPageSourceUrl();
    const sourceUrl = pageSourceUrl
      ? `?source_url=${encodeURIComponent(pageSourceUrl)}`
      : "";
    const res = await fetch(
      `${API_BASE_URL}/api/v1/public/demo/${encodeURIComponent(slug)}/call-token${sourceUrl}`,
      { method: "POST", headers: { "Content-Type": "application/json" } },
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

  /**
   * Fetches the signed visitor receipt for a completed demo call.
   *
   * @param slug - Public demo slug from the current page.
   * @param receiptToken - Short-lived token returned with the voice token.
   * @returns Promise resolving to the visitor's private outcome.
   * @throws {Error} When the token is missing, expired, or unavailable.
   */
  async getDemoOutcome(
    slug: string,
    receiptToken: string,
  ): Promise<DemoOutcome> {
    const res = await fetch(
      `${API_BASE_URL}/api/v1/public/demo/${encodeURIComponent(slug)}/outcome?token=${encodeURIComponent(receiptToken)}`,
      { cache: "no-store" },
    );
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail || "Demo outcome is unavailable");
    }
    return (await res.json()) as DemoOutcome;
  }

  /**
   * Records one visitor star rating for a demo call.
   *
   * The signed receipt token binds the rating to the visitor's own
   * session; repeat taps update the same stored row. The PostHog funnel
   * event is emitted separately by the caller.
   *
   * @param slug - Public demo slug from the current page.
   * @param receiptToken - Short-lived token returned with the voice token.
   * @param rating - Star value from 1 to 5.
   * @throws {Error} When the rating cannot be recorded.
   */
  async submitDemoFeedback(
    slug: string,
    receiptToken: string,
    rating: number,
  ): Promise<void> {
    const res = await fetch(
      `${API_BASE_URL}/api/v1/public/demo/${encodeURIComponent(slug)}/feedback?token=${encodeURIComponent(receiptToken)}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ rating }),
      },
    );
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail || "Could not record the rating");
    }
  }
}

export const demoPublicService = new DemoPublicService();
