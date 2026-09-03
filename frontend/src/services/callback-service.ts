/**
 * Client for owner-visible callback escalations (soft escalation).
 *
 * @module services/callback-service
 */

import { apiClient } from "@/lib/api/client";

/** Follow-up status of a callback escalation. */
export type EscalationStatus = "new" | "acknowledged" | "resolved";

/** One callback escalation row. */
export interface CallbackEscalation {
  /** Row identifier. */
  id: string;
  /** Owning organization identifier. */
  organization_id: string;
  /** Agent identifier when known. */
  agent_id: string | null;
  /** Voice session identifier when known. */
  session_id: string | null;
  /** Caller callback number. */
  caller_phone: string;
  /** Caller name when known. */
  caller_name: string | null;
  /** What the callback is about. */
  reason: string;
  /** Callback urgency. */
  urgency: "normal" | "urgent";
  /** Follow-up status. */
  status: EscalationStatus;
  /** Whether the owner alert email went out. */
  notified: boolean;
  /** Creation timestamp. */
  created_at: string;
  /** Acknowledgement timestamp. */
  acknowledged_at: string | null;
}

/** Standard service result envelope. */
export interface CallbackServiceResult<T> {
  success: boolean;
  error?: string;
  data?: T;
}

function failure<T>(message: string): CallbackServiceResult<T> {
  return { success: false, error: message };
}

/**
 * Lists escalations newest-first for one organization.
 *
 * @param orgId - Owning organization identifier.
 * @param status - Optional follow-up status filter.
 * @returns Service envelope with the escalation list.
 */
async function listEscalations(
  orgId: string,
  status?: EscalationStatus,
): Promise<CallbackServiceResult<CallbackEscalation[]>> {
  try {
    const query = status ? `?status=${encodeURIComponent(status)}` : "";
    const response = await apiClient.get<CallbackEscalation[]>(
      `/api/v1/organizations/${encodeURIComponent(orgId)}/escalations${query}`,
    );
    return { success: true, data: response.data ?? [] };
  } catch (error) {
    return failure(
      error instanceof Error ? error.message : "Could not load callbacks.",
    );
  }
}

/**
 * Advances one escalation's follow-up status (org admins).
 *
 * @param orgId - Owning organization identifier.
 * @param escalationId - Escalation row identifier.
 * @param status - Target follow-up status.
 * @returns Service envelope with the updated row.
 */
async function markEscalationStatus(
  orgId: string,
  escalationId: string,
  status: EscalationStatus,
): Promise<CallbackServiceResult<CallbackEscalation>> {
  try {
    const response = await apiClient.patch<CallbackEscalation>(
      `/api/v1/organizations/${encodeURIComponent(orgId)}/escalations/${encodeURIComponent(escalationId)}`,
      { status },
    );
    if (!response.data) return failure("Could not update the callback.");
    return { success: true, data: response.data };
  } catch (error) {
    return failure(
      error instanceof Error ? error.message : "Could not update the callback.",
    );
  }
}

export const callbackService = {
  listEscalations,
  markEscalationStatus,
};
