import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const { captureMock, initMock } = vi.hoisted(() => ({
  captureMock: vi.fn(),
  initMock: vi.fn(),
}));

vi.mock("posthog-js", () => ({
  default: {
    init: initMock,
    capture: captureMock,
  },
}));

import {
  __resetAnalyticsForTests,
  initAnalytics,
  isAnalyticsEnabled,
  sanitizeProperties,
  trackEvent,
  trackPageview,
} from "@/lib/analytics/posthog";

const KEY = "NEXT_PUBLIC_POSTHOG_KEY";

describe("posthog analytics", () => {
  const previousKey = process.env[KEY];

  beforeEach(() => {
    vi.clearAllMocks();
    __resetAnalyticsForTests();
    delete process.env[KEY];
    initMock.mockImplementation((_key, config) => config.loaded({}));
  });

  afterEach(() => {
    if (previousKey === undefined) delete process.env[KEY];
    else process.env[KEY] = previousKey;
    __resetAnalyticsForTests();
  });

  it("stays disabled without an API key and never initializes", async () => {
    expect(isAnalyticsEnabled()).toBe(false);
    await initAnalytics();
    trackEvent("demo_played", { demo_slug: "dental" });
    trackPageview("/dental");
    expect(initMock).not.toHaveBeenCalled();
    expect(captureMock).not.toHaveBeenCalled();
  });

  it("initializes once and captures sanitized events", async () => {
    process.env[KEY] = "phc_test";
    await initAnalytics();
    await initAnalytics();
    expect(initMock).toHaveBeenCalledTimes(1);

    trackEvent("interest_submitted", {
      source: "request-demo",
      vertical: "dental",
    });
    expect(captureMock).toHaveBeenCalledWith("interest_submitted", {
      source: "request-demo",
      vertical: "dental",
    });
  });

  it("queues events until the PostHog client is ready", async () => {
    process.env[KEY] = "phc_test";
    let finishInitialization!: () => void;
    initMock.mockImplementation((_key, config) => {
      finishInitialization = config.loaded;
    });

    const initialization = initAnalytics();
    trackEvent("demo_played", { demo_slug: "dental" });

    expect(captureMock).not.toHaveBeenCalled();
    finishInitialization();
    await initialization;

    expect(captureMock).toHaveBeenCalledWith("demo_played", {
      demo_slug: "dental",
    });
  });

  it("strips PII keys before capture", () => {
    expect(
      sanitizeProperties({
        source: "request-demo",
        email: "sam@example.com",
        name: "Sam",
        phone: "+14805550100",
        demo_slug: "dental",
      }),
    ).toEqual({ source: "request-demo", demo_slug: "dental" });
  });

  it("captures pageviews by path only (no query or tokens)", async () => {
    process.env[KEY] = "phc_test";
    await initAnalytics();
    trackPageview("/demo/dental");
    expect(captureMock).toHaveBeenCalledWith("$pageview", {
      $current_url: "/demo/dental",
    });
  });
});
