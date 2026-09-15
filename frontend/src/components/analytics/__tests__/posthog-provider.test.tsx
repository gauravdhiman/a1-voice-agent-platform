import { cleanup, render, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const { initMock, trackPageviewMock, usePathnameMock, callOrder } =
  vi.hoisted(() => ({
    initMock: vi.fn(),
    trackPageviewMock: vi.fn(),
    usePathnameMock: vi.fn(),
    callOrder: [] as string[],
  }));

vi.mock("next/navigation", () => ({ usePathname: usePathnameMock }));
vi.mock("@/lib/analytics/posthog", () => ({
  initAnalytics: initMock,
  trackPageview: trackPageviewMock,
}));

import { AnalyticsProvider } from "../posthog-provider";

describe("AnalyticsProvider", () => {
  beforeEach(() => {
    vi.stubEnv("NEXT_PUBLIC_POSTHOG_KEY", "phc_test");
    initMock.mockReset();
    trackPageviewMock.mockReset();
    usePathnameMock.mockReset();
    usePathnameMock.mockReturnValue(null);
    callOrder.length = 0;
    initMock.mockImplementation(() => {
      callOrder.push("init");
      return Promise.resolve();
    });
    trackPageviewMock.mockImplementation((path: string) =>
      callOrder.push(`pageview:${path}`),
    );
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllEnvs();
  });

  it("waits for initialization before tracking when Next has no pathname yet", async () => {
    let finishInitialization!: () => void;
    initMock.mockImplementation(() => {
      callOrder.push("init");
      return new Promise<void>((resolve) => {
        finishInitialization = resolve;
      });
    });

    render(
      <AnalyticsProvider>
        <div>marketing page</div>
      </AnalyticsProvider>,
    );

    await waitFor(() => expect(initMock).toHaveBeenCalledTimes(1));
    expect(trackPageviewMock).not.toHaveBeenCalled();

    finishInitialization();

    await waitFor(() =>
      expect(trackPageviewMock).toHaveBeenCalledWith(window.location.pathname),
    );

    expect(initMock).toHaveBeenCalledTimes(1);
    expect(callOrder).toEqual([
      "init",
      `pageview:${window.location.pathname}`,
    ]);
  });

  it("tracks only the Next pathname when it is available", async () => {
    usePathnameMock.mockReturnValue("/request-demo");

    render(
      <AnalyticsProvider>
        <div>request demo page</div>
      </AnalyticsProvider>,
    );

    await waitFor(() =>
      expect(trackPageviewMock).toHaveBeenCalledWith("/request-demo"),
    );

    expect(callOrder).toEqual(["init", "pageview:/request-demo"]);
  });
});
