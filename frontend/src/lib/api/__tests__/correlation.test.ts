import { afterEach, describe, expect, it, vi } from "vitest";
import { createTraceparent, readRequestId } from "../correlation";

describe("API correlation", () => {
  afterEach(() => vi.unstubAllGlobals());
  it("omits context when secure randomness is unavailable", () => {
    vi.stubGlobal("crypto", undefined);
    expect(createTraceparent()).toBeUndefined();
    vi.stubGlobal("crypto", {});
    expect(createTraceparent()).toBeUndefined();
  });
  it("generates valid distinct contexts without user data", () => {
    const first = createTraceparent();
    expect(first).toMatch(/^00-[0-9a-f]{32}-[0-9a-f]{16}-01$/);
    expect(createTraceparent()).not.toBe(first);
  });
  it("accepts only a bounded UUID response ID", () => {
    const id = "01234567-89ab-4def-8123-456789abcdef";
    expect(readRequestId(new Headers({ "x-request-id": id }))).toBe(id);
    expect(
      readRequestId(new Headers({ "x-request-id": "private@example.com" })),
    ).toBeUndefined();
    expect(readRequestId(new Headers())).toBeUndefined();
  });
});
