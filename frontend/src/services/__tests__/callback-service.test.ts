import { beforeEach, describe, expect, it, vi } from "vitest";

const { postMock, getMock, patchMock } = vi.hoisted(() => ({
  postMock: vi.fn(),
  getMock: vi.fn(),
  patchMock: vi.fn(),
}));

vi.mock("@/lib/api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api/client")>();
  return {
    ...actual,
    apiClient: {
      post: postMock,
      get: getMock,
      patch: patchMock,
    },
  };
});

import { callbackService } from "@/services/callback-service";

describe("callbackService", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("lists escalations for the organization", async () => {
    const rows = [{ id: "esc-1", status: "new" }];
    getMock.mockResolvedValue({ data: rows });

    const result = await callbackService.listEscalations("org-1");

    expect(result).toEqual({ success: true, data: rows });
    expect(getMock).toHaveBeenCalledWith(
      "/api/v1/organizations/org-1/escalations",
    );
  });

  it("passes the status filter through", async () => {
    getMock.mockResolvedValue({ data: [] });

    await callbackService.listEscalations("org-1", "new");

    expect(getMock).toHaveBeenCalledWith(
      "/api/v1/organizations/org-1/escalations?status=new",
    );
  });

  it("returns a safe error when listing fails", async () => {
    getMock.mockRejectedValue(new Error("Network down"));

    const result = await callbackService.listEscalations("org-1");

    expect(result.success).toBe(false);
    expect(result.error).toBe("Network down");
  });

  it("marks an escalation resolved", async () => {
    const row = { id: "esc-1", status: "resolved" };
    patchMock.mockResolvedValue({ data: row });

    const result = await callbackService.markEscalationStatus(
      "org-1",
      "esc-1",
      "resolved",
    );

    expect(result).toEqual({ success: true, data: row });
    expect(patchMock).toHaveBeenCalledWith(
      "/api/v1/organizations/org-1/escalations/esc-1",
      { status: "resolved" },
    );
  });
});
