import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { getCurrentPageSourceUrl } from "@/lib/source-url";

describe("getCurrentPageSourceUrl", () => {
  let originalUrl: string;

  beforeEach(() => {
    originalUrl = window.location.href;
    window.history.replaceState({}, "", "/support?customer=private#details");
  });

  afterEach(() => {
    window.history.replaceState({}, "", originalUrl);
  });

  it("removes query and fragment data from the page source", () => {
    expect(getCurrentPageSourceUrl()).toBe(
      `${window.location.origin}/support`,
    );
  });
});
