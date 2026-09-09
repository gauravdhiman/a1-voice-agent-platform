import { beforeEach, describe, expect, it } from "vitest";
import {
  INVITE_WELCOME_STORAGE_KEY,
  consumeInviteWelcome,
  markInviteWelcomePending,
  peekInviteWelcome,
} from "@/lib/invite-welcome";

function createMemoryStorage(): Storage {
  const values = new Map<string, string>();

  return {
    get length() {
      return values.size;
    },
    clear: () => values.clear(),
    getItem: (key) => values.get(key) ?? null,
    key: (index) => Array.from(values.keys())[index] ?? null,
    removeItem: (key) => values.delete(key),
    setItem: (key, value) => values.set(key, String(value)),
  };
}

function ensureStorage(name: "localStorage" | "sessionStorage"): void {
  const existing = (globalThis as unknown as Record<string, Storage | undefined>)[
    name
  ];
  if (existing) {
    existing.clear();
    return;
  }

  const replacement = createMemoryStorage();
  Object.defineProperty(globalThis, name, {
    configurable: true,
    value: replacement,
  });
  Object.defineProperty(window, name, {
    configurable: true,
    value: replacement,
  });
}

describe("invite-welcome", () => {
  beforeEach(() => {
    ensureStorage("sessionStorage");
    ensureStorage("localStorage");
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
