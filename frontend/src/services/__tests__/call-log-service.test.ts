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
});
