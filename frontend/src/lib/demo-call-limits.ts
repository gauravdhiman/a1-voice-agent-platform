/** Shared presentation helpers for platform-admin demo call budgets. */

export const DEMO_UNLIMITED = -1;
export const DEMO_TRIAL_EXHAUSTED_MESSAGE =
  "This demo agent has used all available trial calls. Please contact the platform administrator for further details or to have the demo re-enabled.";

/** Return true when a demo agent has no reservations available. */
export function isDemoCallLimitReached(
  callsRemaining: number | null | undefined,
): boolean {
  return callsRemaining === 0;
}

/** Format a remaining-call limit for a visitor-facing summary. */
export function formatDemoCallsRemaining(
  callsRemaining: number | null | undefined,
): string | null {
  if (callsRemaining === null || callsRemaining === undefined) return null;
  if (callsRemaining === DEMO_UNLIMITED) return "Unlimited trial calls";
  if (callsRemaining === 0) return "No trial calls remaining";
  return `${callsRemaining} trial call${callsRemaining === 1 ? "" : "s"} remaining`;
}

/** Format a duration limit expressed in seconds for visitor-facing copy. */
export function formatDemoDuration(
  durationSeconds: number | null | undefined,
): string | null {
  if (durationSeconds === null || durationSeconds === undefined) return null;
  if (durationSeconds === DEMO_UNLIMITED) return "No maximum call duration";
  if (durationSeconds <= 0) return null;
  const minutes = Math.floor(durationSeconds / 60);
  const seconds = durationSeconds % 60;
  if (minutes > 0 && seconds === 0) {
    return `Maximum ${minutes} minute${minutes === 1 ? "" : "s"} per call`;
  }
  if (minutes > 0) return `Maximum ${minutes}m ${seconds}s per call`;
  return `Maximum ${seconds} second${seconds === 1 ? "" : "s"} per call`;
}
