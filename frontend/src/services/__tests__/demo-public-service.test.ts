import { beforeEach, describe, expect, it, vi } from "vitest";

import { demoPublicService } from "@/services/demo-public-service";

describe("demoPublicService", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("fetches public demo metadata with an encoded slug", async () => {
    const fetchMock = vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          id: "agent-1",
          name: "Acme Demo",
          demo_slug: "acme-demo",
          persona: "A helpful receptionist",
          mission: "Answer questions",
          tone: "Friendly",
          public_description: "Try our voice assistant.",
          organization_id: "org-1",
          organization_name: "Acme",
        }),
        { status: 200 },
      ),
    );

    const result = await demoPublicService.getDemoAgent("Acme Dental/Demo");

    expect(result.public_description).toBe("Try our voice assistant.");
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/public/demo/Acme%20Dental%2FDemo"),
      expect.objectContaining({ cache: "no-store" }),
    );
  });

  it("requests a public demo call token with the correct method", async () => {
    const fetchMock = vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          token: "voice-token",
          wsUrl: "wss://voice.example/ws",
          sessionId: "session-1",
        }),
        { status: 200 },
      ),
    );

    const result = await demoPublicService.getCallToken("acme-demo");

    expect(result.sessionId).toBe("session-1");
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/public/demo/acme-demo/call-token"),
      expect.objectContaining({
        method: "POST",
        headers: { "Content-Type": "application/json" },
      }),
    );
  });

  it("surfaces safe public-call errors from the API", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          detail: {
            code: "VOICE_ASSISTANT_UNAVAILABLE",
            message: "Please contact the business.",
          },
        }),
        { status: 503 },
      ),
    );

    await expect(demoPublicService.getCallToken("acme-demo")).rejects.toThrow(
      /contact the business/i,
    );
  });
});
