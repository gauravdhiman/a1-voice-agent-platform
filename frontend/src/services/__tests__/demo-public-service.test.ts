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
          demo_calls_remaining: 3,
          demo_max_call_duration_seconds: 600,
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
          receiptToken: "receipt-token",
          demo_calls_remaining: 2,
          demo_max_call_duration_seconds: 600,
        }),
        { status: 200 },
      ),
    );

    const result = await demoPublicService.getCallToken("acme-demo");

    expect(result.sessionId).toBe("session-1");
    expect(result.receiptToken).toBe("receipt-token");
    expect(result.demo_calls_remaining).toBe(2);
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

  it("surfaces the exhausted trial message from the API", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          detail: {
            code: "DEMO_TRIAL_EXHAUSTED",
            message:
              "This demo agent has used all available trial calls. Please contact the platform administrator for further details or to have the demo re-enabled.",
          },
        }),
        { status: 429 },
      ),
    );

    await expect(demoPublicService.getCallToken("acme-demo")).rejects.toThrow(
      /contact the platform administrator.*re-enabled/i,
    );
  });

  it("fetches the signed visitor outcome receipt", async () => {
    const fetchMock = vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          demo_slug: "acme-demo",
          agent_name: "Alex",
          organization_name: "Acme",
          status: "completed",
          actions: [],
          expires_at: "2026-09-01T00:00:00Z",
        }),
        { status: 200 },
      ),
    );

    const result = await demoPublicService.getDemoOutcome(
      "Acme Dental/Demo",
      "signed receipt/token",
    );

    expect(result.status).toBe("completed");
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining(
        "/api/v1/public/demo/Acme%20Dental%2FDemo/outcome?token=signed%20receipt%2Ftoken",
      ),
      expect.objectContaining({ cache: "no-store" }),
    );
  });

  it("posts one visitor rating bound to the receipt token", async () => {
    const fetchMock = vi
      .spyOn(global, "fetch")
      .mockResolvedValue(
        new Response(JSON.stringify({ received: true }), { status: 200 }),
      );

    await demoPublicService.submitDemoFeedback("acme-demo", "receipt-token", 5);

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining(
        "/api/v1/public/demo/acme-demo/feedback?token=receipt-token",
      ),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ rating: 5 }),
      }),
    );
  });

  it("surfaces rating failures without leaking internals", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "Could not record the rating" }), {
        status: 500,
      }),
    );

    await expect(
      demoPublicService.submitDemoFeedback("acme-demo", "receipt-token", 5),
    ).rejects.toThrow("Could not record the rating");
  });
});
