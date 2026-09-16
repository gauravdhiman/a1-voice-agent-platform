import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  platformAdmin: false,
  analytics: vi.fn(),
}));

vi.mock("@/contexts/auth-context", () => ({
  useAuth: () => ({
    user: {
      id: "platform-user",
      hasRole: (role: string) => role === "platform_admin" && mocks.platformAdmin,
    },
  }),
}));
vi.mock("@/services/call-log-service", () => ({
  callLogService: { getPlatformAnalytics: mocks.analytics },
}));

import PlatformDashboardPage from "../page";

const report = {
  active_organizations: 4,
  total_calls_week: 8,
  total_calls_month: 24,
  avg_duration_seconds: 35,
  selected_period_days: 30,
  selected_status: null,
  selected_total_calls: 24,
  selected_active_organizations: 4,
  selected_average_duration_seconds: 42,
  available_statuses: ["completed", "failed"],
  calls_by_agent: [],
  calls_by_day: [
    { date: "2026-09-14", calls: 10 },
    { date: "2026-09-15", calls: 14 },
  ],
  calls_by_hour: Array.from({ length: 24 }, (_, hour) => ({
    hour,
    calls: hour === 16 ? 6 : 0,
  })),
  calls_by_status: [
    { status: "completed", count: 20 },
    { status: "failed", count: 4 },
  ],
};

function mount() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <PlatformDashboardPage />
    </QueryClientProvider>,
  );
}

function setChartBounds(chart: HTMLElement, width: number, height = 128) {
  Object.defineProperty(chart, "getBoundingClientRect", {
    configurable: true,
    value: () => ({
      x: 0,
      y: 0,
      left: 0,
      right: width,
      top: 0,
      bottom: height,
      width,
      height,
      toJSON: () => ({}),
    }),
  });
}

beforeEach(() => {
  vi.clearAllMocks();
  mocks.platformAdmin = false;
  mocks.analytics.mockResolvedValue(report);
});
afterEach(cleanup);

describe("platform overview", () => {
  it("does not request platform analytics for a workspace user", () => {
    mount();
    expect(screen.getByRole("alert").textContent).toContain("Only platform administrators");
    expect(mocks.analytics).not.toHaveBeenCalled();
  });

  it("shows cross-organization volume and filterable outcomes for platform admins", async () => {
    mocks.platformAdmin = true;
    const user = userEvent.setup();
    mount();
    await screen.findByText("Organizations with calls");

    expect(screen.getByRole("heading", { name: "Platform overview" })).toBeTruthy();
    expect(screen.getByText("All organizations")).toBeTruthy();
    expect(screen.getByText("Platform call volume")).toBeTruthy();
    expect(screen.getByText(/Busiest: 16:00/)).toBeTruthy();
    expect(screen.getByRole("link", { name: "Selected workspace" })).toBeTruthy();
    expect(mocks.analytics).toHaveBeenCalledWith("last_30_days", undefined);

    const periodFilter = screen.getByLabelText("Platform reporting period") as HTMLSelectElement;
    expect(Array.from(periodFilter.options).map((option) => option.textContent)).toEqual([
      "Today",
      "Yesterday",
      "Last 7 days",
      "Last 15 days",
      "Last 30 days",
    ]);

    await user.selectOptions(periodFilter, "last_7_days");
    await waitFor(() => expect(mocks.analytics).toHaveBeenCalledWith("last_7_days", undefined));
    await user.selectOptions(periodFilter, "last_15_days");
    await waitFor(() => expect(mocks.analytics).toHaveBeenCalledWith("last_15_days", undefined));
    await user.selectOptions(periodFilter, "today");
    await waitFor(() => expect(mocks.analytics).toHaveBeenCalledWith("today", undefined));
    await user.selectOptions(screen.getByLabelText("Platform call status filter"), "failed");
    await waitFor(() => expect(mocks.analytics).toHaveBeenCalledWith("today", "failed"));
  });

  it("uses immediate pointer readouts for all platform charts", async () => {
    mocks.platformAdmin = true;
    mount();
    await screen.findByText("Organizations with calls");

    const volume = screen.getByRole("group", {
      name: /Platform daily call volume/,
    });
    const markers = Array.from(volume.querySelectorAll("[data-chart-marker]"));
    const markerClasses = markers.map((marker) => marker.getAttribute("class"));
    expect(markers).toHaveLength(2);
    expect(markerClasses[0]).toContain("h-1.5 w-1.5");
    expect(markerClasses[0]).toContain("rounded-full");
    expect(markerClasses.every((className) => className === markerClasses[0])).toBe(
      true,
    );
    setChartBounds(volume, 100);
    fireEvent.pointerMove(volume, { pointerType: "mouse", clientX: 80 });
    expect(screen.getByRole("tooltip").getAttribute("aria-label")).toBe(
      "Sep 15, 2026, 14 calls",
    );
    expect(
      Array.from(volume.querySelectorAll("[data-chart-marker]")).map((marker) =>
        marker.getAttribute("class"),
      ),
    ).toEqual(markerClasses);

    fireEvent.pointerLeave(volume, { pointerType: "mouse" });
    const hours = screen.getByRole("group", {
      name: /Calls by hour in UTC/,
    });
    setChartBounds(hours, 240, 96);
    fireEvent.pointerMove(hours, { pointerType: "mouse", clientX: 165 });
    expect(screen.getByRole("tooltip").getAttribute("aria-label")).toBe(
      "16:00–17:00, 6 calls",
    );

    fireEvent.pointerLeave(hours, { pointerType: "mouse" });
    const outcomes = screen.getByRole("group", {
      name: /Platform call outcomes by status/,
    });
    setChartBounds(outcomes, 240, 56);
    fireEvent.pointerMove(outcomes, { pointerType: "mouse", clientX: 220 });
    expect(screen.getByRole("tooltip").getAttribute("aria-label")).toBe(
      "Failed, 4 calls",
    );
  });

  it("reports platform analytics failures without showing fabricated totals", async () => {
    mocks.platformAdmin = true;
    mocks.analytics.mockRejectedValue(new Error("unavailable"));
    mount();
    await screen.findByRole("alert");
    expect(screen.queryByText("Organizations with calls")).toBeNull();
    expect(screen.getByRole("button", { name: "Try again" })).toBeTruthy();
  });
});
