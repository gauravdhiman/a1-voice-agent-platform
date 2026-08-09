import { apiClient } from "@/lib/api/client";

export interface CallLog {
  id: string;
  call_sid: string;
  organization_id: string;
  agent_id: string | null;
  caller_number: string | null;
  called_number: string | null;
  status: string;
  duration: number | null;
  credits_consumed: number;
  credit_transaction_id: string | null;
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
  total_calls_week: number;
  total_calls_month: number;
  avg_duration_seconds: number;
  calls_by_agent: { agent_id: string; agent_name: string; count: number }[];
  calls_by_hour: { hour: number; calls: number }[];
  calls_by_status: { status: string; count: number }[];
}

export interface CallLogListParams {
  agent_id?: string;
  status?: string;
  date_from?: string;
  date_to?: string;
  page?: number;
  page_size?: number;
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
    if (params.date_from) query.set("date_from", params.date_from);
    if (params.date_to) query.set("date_to", params.date_to);
    if (params.page) query.set("page", String(params.page));
    if (params.page_size) query.set("page_size", String(params.page_size));

    const url = `${this.base}/organization/${orgId}${query.toString() ? "?" + query.toString() : ""}`;
    const response = await apiClient.get<CallLogsResponse>(url);
    return response.data;
  }

  async getAnalytics(orgId: string): Promise<CallAnalytics> {
    const response = await apiClient.get<CallAnalytics>(
      `${this.base}/organization/${orgId}/analytics`,
    );
    return response.data;
  }
}

export const callLogService = new CallLogService();
