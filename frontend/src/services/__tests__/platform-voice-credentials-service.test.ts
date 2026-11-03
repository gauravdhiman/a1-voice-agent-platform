import { beforeEach, describe, expect, it, vi } from "vitest";

const { apiClient } = vi.hoisted(() => ({
  apiClient: {
    get: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

vi.mock("@/lib/api/client", () => ({ apiClient }));

import { platformVoiceCredentialsService } from "../platform-voice-credentials-service";

describe("platformVoiceCredentialsService", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiClient.get.mockResolvedValue({ data: { providers: {} } });
    apiClient.put.mockResolvedValue({ data: { configured: true } });
    apiClient.delete.mockResolvedValue({ data: undefined });
  });

  it("loads secret-free status from the platform voice credentials endpoint", async () => {
    const result = await platformVoiceCredentialsService.getCredentials();

    expect(result.success).toBe(true);
    expect(apiClient.get).toHaveBeenCalledWith(
      "/api/v1/platform/api-credentials/",
    );
  });

  it("writes one provider key to its dedicated endpoint", async () => {
    const result = await platformVoiceCredentialsService.saveCredential(
      "google",
      "new-key",
    );

    expect(result.success).toBe(true);
    expect(apiClient.put).toHaveBeenCalledWith(
      "/api/v1/platform/api-credentials/google",
      { api_key: "new-key" },
    );
  });

  it("removes one provider key", async () => {
    const result = await platformVoiceCredentialsService.removeCredential("openai");

    expect(result.success).toBe(true);
    expect(apiClient.delete).toHaveBeenCalledWith(
      "/api/v1/platform/api-credentials/openai",
    );
  });

  it("returns a safe failure result", async () => {
    apiClient.put.mockRejectedValue(new Error("request failed"));

    await expect(
      platformVoiceCredentialsService.saveCredential("google", "new-key"),
    ).resolves.toEqual({ success: false, error: "request failed" });
  });
});
