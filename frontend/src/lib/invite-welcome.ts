/**
 * Session-scoped invite join context: welcome toast + preferred current org.
 *
 * Invite flows (email signup, OAuth handoff) set this before navigating to the
 * dashboard. OrganizationProvider uses the organization id to select the
 * invited tenant; InviteWelcomeToast consumes the payload for a one-shot toast.
 */

export const INVITE_WELCOME_STORAGE_KEY = "invite_welcome_v1";

export interface InviteWelcomePayload {
  /** Display name of the organization the user joined, when known. */
  organizationName: string | null;
  /** Organization id to select as current after invite acceptance. */
  organizationId: string | null;
}

/**
 * Persist invite join context and optionally set the current organization id.
 *
 * @param options Organization id/name from invitation processing
 */
export function markInviteWelcomePending(options?: {
  organizationName?: string | null;
  organizationId?: string | null;
}): void {
  if (typeof window === "undefined") {
    return;
  }

  const organizationId = options?.organizationId?.trim() || null;
  const organizationName = options?.organizationName?.trim() || null;

  const payload: InviteWelcomePayload = {
    organizationName,
    organizationId,
  };

  try {
    sessionStorage.setItem(INVITE_WELCOME_STORAGE_KEY, JSON.stringify(payload));
  } catch {
    // Ignore quota / private-mode failures; welcome toast is non-critical.
  }

  // Select the invited org as current immediately so OrganizationProvider
  // restores it on the next dashboard load.
  if (organizationId) {
    try {
      localStorage.setItem("currentOrganizationId", organizationId);
    } catch {
      // Ignore storage failures.
    }
  }
}

/**
 * Peek at pending invite context without clearing it.
 *
 * Used by OrganizationProvider when choosing the current organization.
 */
export function peekInviteWelcome(): InviteWelcomePayload | null {
  if (typeof window === "undefined") {
    return null;
  }

  try {
    const raw = sessionStorage.getItem(INVITE_WELCOME_STORAGE_KEY);
    if (!raw) {
      return null;
    }
    return _parsePayload(raw);
  } catch {
    return null;
  }
}

/**
 * Read and clear the pending invite welcome payload.
 *
 * @returns Welcome payload when one was pending, otherwise null
 */
export function consumeInviteWelcome(): InviteWelcomePayload | null {
  if (typeof window === "undefined") {
    return null;
  }

  try {
    const raw = sessionStorage.getItem(INVITE_WELCOME_STORAGE_KEY);
    if (!raw) {
      return null;
    }
    sessionStorage.removeItem(INVITE_WELCOME_STORAGE_KEY);
    return _parsePayload(raw);
  } catch {
    sessionStorage.removeItem(INVITE_WELCOME_STORAGE_KEY);
    return null;
  }
}

function _parsePayload(raw: string): InviteWelcomePayload {
  const parsed = JSON.parse(raw) as InviteWelcomePayload;
  return {
    organizationName:
      typeof parsed.organizationName === "string" && parsed.organizationName.trim()
        ? parsed.organizationName.trim()
        : null,
    organizationId:
      typeof parsed.organizationId === "string" && parsed.organizationId.trim()
        ? parsed.organizationId.trim()
        : null,
  };
}
