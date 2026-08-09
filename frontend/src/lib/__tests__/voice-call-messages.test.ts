import { describe, expect, it } from "vitest";
import {
  getPublicVoiceCallErrorMessage,
  PUBLIC_VOICE_ASSISTANT_BUSY_MESSAGE,
  PUBLIC_VOICE_ASSISTANT_UNAVAILABLE_MESSAGE,
} from "@/lib/voice-call-messages";

describe("getPublicVoiceCallErrorMessage", () => {
  it("hides internal credit details from public callers", () => {
    expect(
      getPublicVoiceCallErrorMessage({
        detail: {
          code: "INSUFFICIENT_CREDITS",
          message: "Insufficient credits to start a voice call.",
        },
      }),
    ).toBe(PUBLIC_VOICE_ASSISTANT_UNAVAILABLE_MESSAGE);
  });

  it("explains that a busy assistant can be retried", () => {
    expect(
      getPublicVoiceCallErrorMessage({
        detail: { code: "MAX_CONCURRENT_CALLS", message: "Plan limit reached" },
      }),
    ).toBe(PUBLIC_VOICE_ASSISTANT_BUSY_MESSAGE);
  });

  it("turns a browser 1006 into an actionable public message", () => {
    expect(
      getPublicVoiceCallErrorMessage(
        new Error("WEBSOCKET_ERROR: WebSocket connection error (1006)"),
      ),
    ).toBe(PUBLIC_VOICE_ASSISTANT_UNAVAILABLE_MESSAGE);
  });

  it("does not expose arbitrary backend details to public callers", () => {
    expect(
      getPublicVoiceCallErrorMessage({ detail: "Database timeout" }),
    ).toMatch(/contact the business/i);
  });
});
