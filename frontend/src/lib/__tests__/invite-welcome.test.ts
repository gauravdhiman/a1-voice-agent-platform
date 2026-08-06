import { beforeEach, describe, expect, it } from "vitest";
import {
  INVITE_WELCOME_STORAGE_KEY,
  consumeInviteWelcome,
  markInviteWelcomePending,
  peekInviteWelcome,
} from "@/lib/invite-welcome";

describe("invite-welcome", () => {
  beforeEach(() => {
    sessionStorage.clear();
    localStorage.clear();
  });

  it("stores and peeks invite context without clearing", () => {
    markInviteWelcomePending({
      organizationName: "Acme Plumbing",
      organizationId: "org-1",
    });

    expect(peekInviteWelcome()).toEqual({
      organizationName: "Acme Plumbing",
      organizationId: "org-1",
    });
    expect(sessionStorage.getItem(INVITE_WELCOME_STORAGE_KEY)).not.toBeNull();
    expect(localStorage.getItem("currentOrganizationId")).toBe("org-1");
  });

  it("consumes a pending invite welcome once", () => {
    markInviteWelcomePending({ organizationName: "Acme Plumbing" });

    const first = consumeInviteWelcome();
    expect(first).toEqual({
      organizationName: "Acme Plumbing",
      organizationId: null,
    });
    expect(sessionStorage.getItem(INVITE_WELCOME_STORAGE_KEY)).toBeNull();
    expect(consumeInviteWelcome()).toBeNull();
  });

  it("returns null when nothing is pending", () => {
    expect(consumeInviteWelcome()).toBeNull();
    expect(peekInviteWelcome()).toBeNull();
  });
});
