import { beforeEach, describe, expect, it, vi } from "vitest";

const { getMock, getBlobMock } = vi.hoisted(() => ({
  getMock: vi.fn(),
  getBlobMock: vi.fn(),
}));

vi.mock("@/lib/api/client", () => ({
  apiClient: {
    get: getMock,
    getBlob: getBlobMock,
  },
}));

import { callLogService } from "@/services/call-log-service";

describe("callLogService recording access", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("downloads a recording through the authenticated API client", async () => {
    const blob = new Blob(["audio"], { type: "audio/wav" });
    getBlobMock.mockResolvedValue(blob);

    await expect(callLogService.downloadRecording("call-123")).resolves.toBe(
      blob,
    );
    expect(getBlobMock).toHaveBeenCalledWith(
      "/api/v1/calls/call-123/recording",
    );
  });

  it("requests only recorded calls when the recordings view is filtered", async () => {
    getMock.mockResolvedValue({
      data: { items: [], total: 0, page: 1, page_size: 25, total_pages: 1 },
    });

    await callLogService.listCallLogs("org-1", {
      agent_id: "agent-1",
      recording_only: true,
      page: 1,
      page_size: 25,
    });

    expect(getMock).toHaveBeenCalledWith(
      "/api/v1/calls/organization/org-1?agent_id=agent-1&recording_only=true&page=1&page_size=25",
    );
  });

  it("requests calls for a selected source", async () => {
    getMock.mockResolvedValue({
      data: { items: [], total: 0, page: 1, page_size: 25, total_pages: 1 },
    });

    await callLogService.listCallLogs("org-1", {
      source_type: "web_embed",
      page: 1,
      page_size: 25,
    });

    expect(getMock).toHaveBeenCalledWith(
      "/api/v1/calls/organization/org-1?source_type=web_embed&page=1&page_size=25",
    );
  });

  it("sends a half-open date window for the recent-call preview", async () => {
    getMock.mockResolvedValue({
      data: { items: [], total: 0, page: 1, page_size: 25, total_pages: 1 },
    });
    const start = "2025-03-09T05:00:00.000Z";
    const endExclusive = "2025-03-10T04:00:00.000Z";

    await callLogService.listCallLogs("org-1", {
      date_from: start,
      date_to_exclusive: endExclusive,
      page: 1,
      page_size: 6,
    });

    const requestUrl = getMock.mock.calls[0][0] as string;
    const query = new URLSearchParams(requestUrl.split("?")[1]);
    expect(query.get("date_from")).toBe(start);
    expect(query.get("date_to_exclusive")).toBe(endExclusive);
    expect(query.has("date_to")).toBe(false);
  });

  it("requests analytics for the selected period, status, and organization timezone", async () => {
    getMock.mockResolvedValue({ data: { selected_total_calls: 4 } });

    await callLogService.getAnalytics(
      "org-1",
      "last_7_days",
      "failed",
      "America/Phoenix",
    );

    expect(getMock).toHaveBeenCalledWith(
      "/api/v1/calls/organization/org-1/analytics?period_days=7&timezone_name=America%2FPhoenix&status=failed",
    );
  });

  it("loads a filtered platform report through the platform-only route", async () => {
    getMock.mockResolvedValue({ data: { selected_total_calls: 2 } });

    await callLogService.getPlatformAnalytics("last_7_days", "failed");

    expect(getMock).toHaveBeenCalledWith(
      "/api/v1/calls/platform/analytics?period_days=7&status=failed",
    );
  });

  it("encodes calendar days and the new 15-day rolling period", async () => {
    getMock.mockResolvedValue({ data: { selected_total_calls: 0 } });

    await callLogService.getAnalytics(
      "org-1",
      "yesterday",
      undefined,
      "America/Phoenix",
    );
    expect(getMock).toHaveBeenLastCalledWith(
      "/api/v1/calls/organization/org-1/analytics?period=yesterday&timezone_name=America%2FPhoenix",
    );

    await callLogService.getPlatformAnalytics("last_15_days");
    expect(getMock).toHaveBeenLastCalledWith(
      "/api/v1/calls/platform/analytics?period_days=15",
    );
  });
});
