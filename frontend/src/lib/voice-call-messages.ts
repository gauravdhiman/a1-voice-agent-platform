/**
 * Safe, user-facing messages for unauthenticated voice call surfaces.
 *
 * Public visitors should receive guidance that helps them recover or contact
 * the business. Internal plan, credit, and concurrency details belong in the
 * authenticated platform UI and service logs, not in an embedded website.
 */

export const PUBLIC_VOICE_ASSISTANT_UNAVAILABLE_MESSAGE =
  "This voice assistant is temporarily unavailable. Please try again later or contact the business for assistance.";

export const PUBLIC_VOICE_ASSISTANT_BUSY_MESSAGE =
  "This voice assistant is currently busy helping other callers. Please try again in a few minutes or contact the business for assistance.";

export const PUBLIC_DEMO_TRIAL_EXHAUSTED_MESSAGE =
  "This demo agent has used all available trial calls. Please contact the platform administrator for further details or to have the demo re-enabled.";

const PUBLIC_VOICE_CONNECTION_ERROR_MESSAGE =
  "We couldn't connect to the voice assistant. Please try again later or contact the business if the problem continues.";

interface VoiceErrorDetails {
  code?: string;
  message?: string;
}

/**
 * Extract a structured public voice error from an API or WebSocket payload.
 *
 * @param error - Unknown error value from fetch, Pipecat, or an API response.
 * @returns The structured code/message pair when one is available.
 */
function readVoiceErrorDetails(error: unknown): VoiceErrorDetails {
  if (!error || typeof error !== "object") {
    return {};
  }

  const record = error as Record<string, unknown>;
  const detail = record.detail;
  if (detail && typeof detail === "object" && !Array.isArray(detail)) {
    const detailRecord = detail as Record<string, unknown>;
    return {
      code:
        typeof detailRecord.code === "string" ? detailRecord.code : undefined,
      message:
        typeof detailRecord.message === "string"
          ? detailRecord.message
          : undefined,
    };
  }

  if (record.data && typeof record.data === "object") {
    return readVoiceErrorDetails(record.data);
  }

  return {
    code: typeof record.code === "string" ? record.code : undefined,
    message: typeof record.message === "string" ? record.message : undefined,
  };
}

/**
 * Convert public voice-call failures into helpful visitor-facing copy.
 *
 * @param error - API response, Error, or Pipecat transport error.
 * @returns Safe message suitable for an external website or public call page.
 */
export function getPublicVoiceCallErrorMessage(error: unknown): string {
  const details = readVoiceErrorDetails(error);
  const rawMessage =
    details.message || (error instanceof Error ? error.message : "");
  const normalized = rawMessage.toLowerCase();

  if (
    details.code === "DEMO_TRIAL_EXHAUSTED" ||
    details.code === "DEMO_CALL_LIMIT_REACHED" ||
    normalized.includes("trial calls") ||
    normalized.includes("demo agent has used all available")
  ) {
    return PUBLIC_DEMO_TRIAL_EXHAUSTED_MESSAGE;
  }

  if (
    details.code === "VOICE_ASSISTANT_BUSY" ||
    details.code === "MAX_CONCURRENT_CALLS" ||
    normalized.includes("concurrent")
  ) {
    return PUBLIC_VOICE_ASSISTANT_BUSY_MESSAGE;
  }

  if (
    details.code === "VOICE_ASSISTANT_UNAVAILABLE" ||
    details.code === "INSUFFICIENT_CREDITS" ||
    normalized.includes("insufficient credit") ||
    normalized.includes("1006") ||
    normalized.includes("websocket")
  ) {
    return PUBLIC_VOICE_ASSISTANT_UNAVAILABLE_MESSAGE;
  }

  if (normalized.includes("daily call limit")) {
    return "This voice assistant has reached its call limit for now. Please try again later or contact the business.";
  }

  return PUBLIC_VOICE_CONNECTION_ERROR_MESSAGE;
}
