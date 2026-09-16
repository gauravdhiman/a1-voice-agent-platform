import { apiClient } from "@/lib/api/client";
import { getRollingPeriodDays } from "@/lib/reporting-period";
import type { ReportingPeriod } from "@/lib/reporting-period";

/** Stable source categories recorded for each voice call. */
export type CallSourceType =
  | "phone"
  | "web_test"
  | "web_embed"
  | "web_demo"
  | "web_public";

export interface CallLog {
  id: string;
  call_sid: string;
  organization_id: string;
  agent_id: string | null;
  caller_number: string | null;
  called_number: string | null;
  source_type: CallSourceType | null;
  source_url: string | null;
  source_domain: string | null;
  status: string;
  failure_code?: string | null;
  failure_message?: string | null;
  duration: number | null;
  credits_consumed: number;
  credit_transaction_id: string | null;
  recording_available: boolean;
  started_at: string | null;
  ended_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface CallLogsResponse {
  items: CallLog[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface CallAnalytics {
  active_organizations: number;
  total_calls_week: number;
  total_calls_month: number;
  avg_duration_seconds: number;
  selected_period_days: number;
  selected_status: string | null;
  selected_total_calls: number;
  selected_active_organizations: number;
  selected_average_duration_seconds: number | null;
  available_statuses: string[];
  calls_by_agent: {
    agent_id: string | null;
    agent_name: string;
    count: number;
    avg_duration_seconds: number | null;
    last_call_at: string | null;
    last_call_status: string | null;
    last_call_duration_seconds: number | null;
    last_call_source_type: CallSourceType | null;
  }[];
  calls_by_day: { date: string; calls: number }[];
  calls_by_hour: { hour: number; calls: number }[];
  calls_by_status: { status: string; count: number }[];
}

export interface CallLogListParams {
  agent_id?: string;
  status?: string;
  source_type?: CallSourceType;
  date_from?: string;
  date_to?: string;
  date_to_exclusive?: string;
  recording_only?: boolean;
  page?: number;
  page_size?: number;
}

function appendPeriodQuery(
  query: URLSearchParams,
  period: ReportingPeriod,
  includeDefault: boolean,
): void {
  const days = getRollingPeriodDays(period);
  if (days === null) {
    query.set("period", period);
  } else if (includeDefault || period !== "last_30_days") {
    query.set("period_days", String(days));
  }
}

class CallLogService {
  private base = "/api/v1/calls";

  async listCallLogs(
    orgId: string,
    params: CallLogListParams = {},
  ): Promise<CallLogsResponse> {
    const query = new URLSearchParams();
    if (params.agent_id) query.set("agent_id", params.agent_id);
    if (params.status) query.set("status", params.status);
    if (params.source_type) query.set("source_type", params.source_type);
    if (params.date_from) query.set("date_from", params.date_from);
    if (params.date_to) query.set("date_to", params.date_to);
    if (params.date_to_exclusive) {
      query.set("date_to_exclusive", params.date_to_exclusive);
    }
    if (params.recording_only) query.set("recording_only", "true");
    if (params.page) query.set("page", String(params.page));
    if (params.page_size) query.set("page_size", String(params.page_size));

    const url = `${this.base}/organization/${orgId}${query.toString() ? "?" + query.toString() : ""}`;
    const response = await apiClient.get<CallLogsResponse>(url);
    return response.data;
  }

  async getAnalytics(
    orgId: string,
    period: ReportingPeriod = "last_30_days",
    status?: string,
    timezoneName = "UTC",
  ): Promise<CallAnalytics> {
    const query = new URLSearchParams();
    appendPeriodQuery(query, period, true);
    query.set("timezone_name", timezoneName);
    if (status) query.set("status", status);
    const response = await apiClient.get<CallAnalytics>(
      `${this.base}/organization/${orgId}/analytics?${query.toString()}`,
    );
    return response.data;
  }

  /**
   * Loads the cross-organization report restricted to platform administrators.
   *
   * @param period - Calendar day or rolling reporting window; defaults to 30 days.
   * @param status - Optional recorded call status to include.
   * @returns Platform-wide call aggregates in UTC.
   */
  async getPlatformAnalytics(
    period: ReportingPeriod = "last_30_days",
    status?: string,
  ): Promise<CallAnalytics> {
    const query = new URLSearchParams();
    appendPeriodQuery(query, period, false);
    if (status) query.set("status", status);
    const queryString = query.toString();
    const suffix = queryString ? `?${queryString}` : "";
    const response = await apiClient.get<CallAnalytics>(
      `${this.base}/platform/analytics${suffix}`,
    );
    return response.data;
  }

  /**
   * Downloads one private call recording through the authenticated backend.
   *
   * @param callLogId - Call log identifier owning the recording
   * @returns Promise resolving to the WAV/audio Blob
   * @throws {Error} When the user lacks admin access or the recording is absent
   */
  async downloadRecording(callLogId: string): Promise<Blob> {
    return apiClient.getBlob(`${this.base}/${callLogId}/recording`);
  }

  /**
   * Deletes one private call recording through the authenticated backend.
   *
   * The audio object is removed from storage; the call log row itself is
   * kept for audit. Requires `call_log:delete` (org admin).
   *
   * @param callLogId - Call log identifier owning the recording
   * @throws {Error} When the user lacks permission or the recording is absent
   */
  async deleteRecording(callLogId: string): Promise<void> {
    await apiClient.delete(`${this.base}/${callLogId}/recording`);
  }

  /**
   * Deletes several recordings in one audited request.
   *
   * Per-item outcomes are returned so partially failed batches surface
   * exactly which recordings were kept. Call-log rows are never removed.
   *
   * @param orgId - Organization every call log must belong to
   * @param callLogIds - One or more (max 100) call log identifiers
   * @returns Map of call log id to per-item deletion status
   * @throws {Error} When the caller lacks org-admin delete rights
   *
   * @example
   * ```typescript
   * const result = await callLogService.deleteRecordings(orgId, ids);
   * if (!result.success) console.error(result.error);
   * ```
   */
  async deleteRecordings(
    orgId: string,
    callLogIds: string[],
  ): Promise<{
    success: boolean;
    error?: string;
    data?: { items: { call_log_id: string; status: string }[]; deleted_count: number };
  }> {
    try {
      const response = await apiClient.post<{
        items: { call_log_id: string; status: string }[];
        deleted_count: number;
      }>(`${this.base}/recordings/delete-batch`, {
        call_log_ids: callLogIds,
        organization_id: orgId,
      });
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: (error as Error).message };
    }
  }
}

export const callLogService = new CallLogService();
