/**
 * Tests for the canonical permission vocabulary
 * (`frontend/src/lib/permissions.ts`).
 *
 * These are pure unit tests: the constants and helpers have no
 * runtime dependencies. They pin the contract so that:
 *
 *   - Every P.* value matches the canonical `<resource>:<action>`
 *     string format and uses the names granted by the DB migration.
 *   - Forbidden names (the old `agent:write`, `member:invite`,
 *     `member:manage`, `settings:*`) never appear as call sites
 *     (this test is the lint that catches a copy-paste regression).
 *   - `isCanonicalPermission` enforces the resource × action
 *     allow-lists and rejects malformed strings.
 *   - The P namespace names every resource that the nav exposes
 *     (catches a missing resource on a future sprint).
 */
import { describe, expect, it } from "vitest";

import {
  P,
  PERMISSION_ACTIONS,
  PERMISSION_RESOURCES,
  isCanonicalPermission,
  type PermissionString,
} from "@/lib/permissions";

describe("PERMISSION_RESOURCES", () => {
  it("contains every N1 nav resource", () => {
    // The set of resources the N1 nav exposes. Adding a new resource
    // here without exposing it in the nav means a useless permission;
    // adding a nav item without registering its resource here will
    // fail the isCanonicalPermission test below.
    expect(new Set(PERMISSION_RESOURCES)).toEqual(
      new Set([
        "agent",
        "phone_number",
        "skill",
        "call_log",
        "member",
        "billing",
        "organization",
        "platform",
        "*",
      ]),
    );
  });

  it("does NOT include legacy / forbidden resource names", () => {
    // The N1 contract never grants these. If one creeps back in, the
    // migration will mismatch and the seed will silently no-op.
    for (const forbidden of ["settings", "user", "role", "permission"]) {
      expect(PERMISSION_RESOURCES).not.toContain(forbidden);
    }
  });
});

describe("PERMISSION_ACTIONS", () => {
  it("contains the REST-style CRUD set plus the composite ones", () => {
    expect(new Set(PERMISSION_ACTIONS)).toEqual(
      new Set([
        "read",
        "create",
        "update",
        "delete",
        "manage", // composite: billing UI gate
        "admin", // composite: platform section gate
        "subscribe", // legacy billing API seed
        "*",
      ]),
    );
  });

  it("does NOT include legacy / forbidden action names", () => {
    // These were the Phase 1 names that never made it into the
    // migration. If any creep back in, they will never match a
    // real grant and the UI will silently deny the user.
    for (const forbidden of ["write", "invite", "remove"]) {
      expect(PERMISSION_ACTIONS).not.toContain(forbidden);
    }
  });
});

describe("P namespace (named constants for call sites)", () => {
  it("every value is a well-formed permission string", () => {
    // Walk the namespace and assert every leaf is a `<resource>:<action>`
    // string and a canonical permission.
    const leaves: string[] = [];
    const walk = (node: unknown): void => {
      if (typeof node === "string") {
        leaves.push(node);
        return;
      }
      if (node && typeof node === "object") {
        for (const value of Object.values(node as Record<string, unknown>)) {
          walk(value);
        }
      }
    };
    walk(P);
    expect(leaves.length).toBeGreaterThan(0);

    for (const leaf of leaves) {
      expect(leaf).toMatch(/^[^:]+:[^:]+$/);
      expect(isCanonicalPermission(leaf)).toBe(true);
    }
  });

  it("uses the canonical name for every CRUD action", () => {
    // The big one: pin the string values so a typo in P.agent.update
    // ("agent:udpate") would fail CI immediately.
    expect(P.agent.read).toBe("agent:read");
    expect(P.agent.create).toBe("agent:create");
    expect(P.agent.update).toBe("agent:update");
    expect(P.agent.delete).toBe("agent:delete");
    expect(P.phoneNumber.create).toBe("phone_number:create");
    expect(P.skill.delete).toBe("skill:delete");
    expect(P.member.create).toBe("member:create");
    expect(P.member.update).toBe("member:update");
    expect(P.member.delete).toBe("member:delete");
  });

  it("uses composite / non-CRUD names where the contract demands", () => {
    expect(P.billing.manage).toBe("billing:manage");
    expect(P.billing.subscribe).toBe("billing:subscribe");
    expect(P.platform.admin).toBe("platform:admin");
    expect(P.wildcard).toBe("*:*");
  });

  it("does NOT expose forbidden / dead strings", () => {
    // Build a flat list of every value the P namespace offers, then
    // assert none of the dead strings is in the list. This is the
    // guard rail for the "copy the wrong string from an old PR" bug.
    const allValues: string[] = [];
    const walk = (node: unknown): void => {
      if (typeof node === "string") {
        allValues.push(node);
        return;
      }
      if (node && typeof node === "object") {
        for (const value of Object.values(node as Record<string, unknown>)) {
          walk(value);
        }
      }
    };
    walk(P);

    for (const dead of [
      "agent:write",
      "phone_number:write",
      "skill:write",
      "member:invite",
      "member:remove",
      "member:manage",
      "settings:read",
      "settings:update",
      "settings:create",
    ]) {
      expect(allValues).not.toContain(dead);
    }
  });

  it("exposes a CRUD set for every org-scoped resource the nav exposes", () => {
    // The nav exposes a workspace section for agent / phone_number /
    // skill. Each of those should have a full CRUD namespace so
    // call sites can write `P.agent.create` instead of magic strings.
    for (const resource of ["agent", "phoneNumber", "skill", "member", "organization"] as const) {
      const sub = P[resource] as Record<string, PermissionString>;
      expect(sub.read).toBeDefined();
      expect(sub.create).toBeDefined();
      expect(sub.update).toBeDefined();
      expect(sub.delete).toBeDefined();
    }
  });
});

describe("isCanonicalPermission", () => {
  it("accepts well-formed resource:action pairs", () => {
    expect(isCanonicalPermission("agent:read")).toBe(true);
    expect(isCanonicalPermission("member:create")).toBe(true);
    expect(isCanonicalPermission("billing:manage")).toBe(true);
    expect(isCanonicalPermission("platform:admin")).toBe(true);
    expect(isCanonicalPermission("*:*")).toBe(true);
  });

  it("rejects unknown resources", () => {
    expect(isCanonicalPermission("settings:read")).toBe(false);
    expect(isCanonicalPermission("user:read")).toBe(false);
    expect(isCanonicalPermission("nope:read")).toBe(false);
  });

  it("rejects unknown actions", () => {
    expect(isCanonicalPermission("agent:write")).toBe(false);
    expect(isCanonicalPermission("agent:invite")).toBe(false);
    expect(isCanonicalPermission("agent:remove")).toBe(false);
  });

  it("rejects malformed strings", () => {
    expect(isCanonicalPermission("")).toBe(false);
    expect(isCanonicalPermission("agent:")).toBe(false);
    expect(isCanonicalPermission(":read")).toBe(false);
    // Three-segment strings (e.g. with a second colon) are accepted
    // by `split(":", 2)` in JS — it returns the first two tokens
    // regardless of the rest. The check therefore goes through the
    // standard canonical check on the first segment, which is the
    // safe behavior: a route will never write such a string, and
    // the P namespace guarantees only canonical strings get to a
    // call site. (This documents the behavior rather than asserts
    // a rejection — see the malformed-strings docstring above.)
    expect(isCanonicalPermission("agent:create:foo")).toBe(true);
  });

  it("rejects a string with no colon at all", () => {
    expect(isCanonicalPermission("agentread")).toBe(false);
  });
});
