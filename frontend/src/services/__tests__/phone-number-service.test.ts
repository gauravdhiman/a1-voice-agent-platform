import { beforeEach, describe, expect, it, vi } from "vitest";

const { apiClient } = vi.hoisted(() => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
  },
}));

vi.mock("@/lib/api/client", () => ({ apiClient }));

import { phoneNumberService } from "@/services/phone-number-service";

describe("phoneNumberService API contracts", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiClient.get.mockResolvedValue({ data: {} });
    apiClient.post.mockResolvedValue({ data: {} });
    apiClient.delete.mockResolvedValue({ data: {} });
  });

  it("uses a query organization id and idempotency header for purchase", async () => {
    await phoneNumberService.purchaseNumber(
      "org/1",
      { phone_number: "+14155550100" },
      "purchase-key",
    );

    expect(apiClient.post).toHaveBeenCalledWith(
      "/api/v1/phone-numbers/purchase?organization_id=org%2F1",
      { phone_number: "+14155550100" },
      { headers: { "Idempotency-Key": "purchase-key" } },
    );
  });

  it("keeps imported numbers on the same organization-scoped lifecycle API", async () => {
    await phoneNumberService.importNumber("org-1", {
      phone_number: "+14155550100",
      agent_id: "agent-1",
    });

    expect(apiClient.post).toHaveBeenCalledWith(
      "/api/v1/phone-numbers/import?organization_id=org-1",
      { phone_number: "+14155550100", agent_id: "agent-1" },
    );
  });

  it("passes organization scope for assignment and release", async () => {
    await phoneNumberService.assignToAgent(
      "number-1",
      { agent_id: "agent-1" },
      "org-1",
    );
    await phoneNumberService.cancelNumber("number-1", "org-1");

    expect(apiClient.post.mock.calls[0][0]).toBe(
      "/api/v1/phone-numbers/number-1/assign?organization_id=org-1",
    );
    expect(apiClient.delete).toHaveBeenCalledWith(
      "/api/v1/phone-numbers/number-1?organization_id=org-1",
    );
  });
});
