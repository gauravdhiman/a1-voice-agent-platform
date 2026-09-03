import { beforeEach, describe, expect, it, vi } from "vitest";

const { postMock, getMock } = vi.hoisted(() => ({
  postMock: vi.fn(),
  getMock: vi.fn(),
}));

vi.mock("@/lib/api/client", async (importOriginal) => {
  const actual =
    await importOriginal<typeof import("@/lib/api/client")>();
  return {
    ...actual,
    apiClient: {
      post: postMock,
      get: getMock,
    },
  };
});

import { leadService } from "@/services/lead-service";

describe("leadService", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("submits interest with the request-demo source by default", async () => {
    postMock.mockResolvedValue({ data: { received: true } });

    const result = await leadService.submitInterestLead({
      name: "Sam Owner",
      email: "sam@example.com",
    });

    expect(result).toEqual({ success: true });
    expect(postMock).toHaveBeenCalledWith("/api/v1/public/leads", {
      name: "Sam Owner",
      business_name: undefined,
      email: "sam@example.com",
      phone: undefined,
      vertical: undefined,
      message: undefined,
      source: "request-demo",
      demo_slug: undefined,
    });
  });

  it("returns a safe error when submission fails", async () => {
    postMock.mockRejectedValue(new Error("Network down"));

    const result = await leadService.submitInterestLead({
      name: "Sam Owner",
      email: "sam@example.com",
    });

    expect(result.success).toBe(false);
    expect(result.error).toBe("Network down");
  });

  it("reports open signup when the backend flag is set", async () => {
    getMock.mockResolvedValue({ data: { public_signup_enabled: true } });

    await expect(leadService.isPublicSignupEnabled()).resolves.toBe(true);
    expect(getMock).toHaveBeenCalledWith("/api/v1/auth/signup-status");
  });

  it("defaults to closed signup when the lookup fails", async () => {
    getMock.mockRejectedValue(new Error("Network down"));

    await expect(leadService.isPublicSignupEnabled()).resolves.toBe(false);
  });
});
