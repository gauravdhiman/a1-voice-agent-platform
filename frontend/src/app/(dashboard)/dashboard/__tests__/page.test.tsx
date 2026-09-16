import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  role: "regular_user",
  orgId: "org-1",
  analytics: vi.fn(),
  api: vi.fn(),
  billing: vi.fn(),
  agentSummary: vi.fn(),
  callList: vi.fn(),
  callbacks: vi.fn(),
}));

vi.mock("@/contexts/auth-context", () => ({
  useAuth: () => ({
    user: {
      id: "user-1",
      hasRole: (role: string) => role === "platform_admin" && mocks.role === role,
    },
  }),
}));
vi.mock("@/contexts/organization-context", () => ({
  useOrganization: () => ({
    currentOrganization: mocks.orgId
      ? { id: mocks.orgId, name: "Test workspace", timezone: "America/Phoenix" }
      : null,
  }),
}));
vi.mock("@/hooks/use-user-permissions", () => ({
  useUserPermissions: () => ({
    isOrgAdmin: mocks.role === "org_admin",
    isPlatformAdmin: mocks.role === "platform_admin",
    canManageBilling: mocks.role !== "regular_user",
    canCreateAgent: mocks.role !== "regular_user",
    isLoading: false,
  }),
}));
vi.mock("@/hooks/use-escalations", () => ({
  useEscalations: (...args: unknown[]) => {
    mocks.callbacks(...args);
    return { data: [], isError: false };
  },
}));
vi.mock("@/hooks/use-call-logs", () => ({
  useCallLogs: (...args: unknown[]) => {
    mocks.callList(...args);
    return { data: { items: callRows }, isError: false };
  },
}));
vi.mock("@/services/call-log-service", () => ({
  callLogService: {
    getAnalytics: mocks.analytics,
    getPlatformAnalytics: async () =>
      (await mocks.api("/api/v1/calls/platform/analytics")).data,
  },
}));
vi.mock("@/services/agent-service", () => ({
  agentService: { getOrganizationAgentSummary: mocks.agentSummary },
}));
vi.mock("@/services/billing-service", () => ({
  billingService: { getBillingSummary: mocks.billing },
}));
vi.mock("@/lib/api/client", () => ({ apiClient: { get: mocks.api } }));

import DashboardPage from "../page";

const callRows = [
  {
    id: "call-1",
    call_sid: "sid-1",
    organization_id: "org-1",
    agent_id: "agent-1",
    caller_number: null,
    called_number: null,
    source_type: "phone",
    source_url: null,
    source_domain: null,
    status: "completed",
    duration: 21,
    credits_consumed: 1,
    credit_transaction_id: null,
    recording_available: false,
    started_at: null,
    ended_at: null,
    created_at: "2026-09-15T12:00:00Z",
    updated_at: "2026-09-15T12:00:00Z",
  },
];

const analyticsData = {
  active_organizations: 3,
  total_calls_week: 9,
  total_calls_month: 20,
  avg_duration_seconds: 10,
  selected_period_days: 30,
  selected_status: null,
  selected_total_calls: 20,
  selected_active_organizations: 1,
  selected_average_duration_seconds: 15,
  available_statuses: ["completed", "failed", "no-answer"],
  calls_by_hour: Array.from({ length: 24 }, (_, hour) => ({
    hour,
    calls: hour === 14 ? 4 : 0,
  })),
  calls_by_day: [
    { date: "2026-09-14", calls: 8 },
    { date: "2026-09-15", calls: 12 },
  ],
  calls_by_agent: [
    {
      agent_id: "agent-1",
      agent_name: "Fixture receptionist",
      count: 12,
      avg_duration_seconds: 15,
      last_call_at: "2026-09-15T12:00:00Z",
      last_call_status: "completed",
      last_call_duration_seconds: 21,
      last_call_source_type: "phone",
    },
  ],
  calls_by_status: [
    { status: "completed", count: 12 },
    { status: "failed", count: 5 },
    { status: "no-answer", count: 2 },
    { status: "in-progress", count: 1 },
  ],
};

function newClient() {
  return new QueryClient({ defaultOptions: { queries: { retry: false } } });
}
function mount(client = newClient()) {
  const view = render(
    <QueryClientProvider client={client}>
      <DashboardPage />
    </QueryClientProvider>,
  );
  return { ...view, client };
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
  mocks.role = "regular_user";
  mocks.orgId = "org-1";
  mocks.analytics.mockResolvedValue(analyticsData);
  mocks.api.mockResolvedValue({ data: analyticsData });
  mocks.agentSummary.mockResolvedValue({ total_agents: 3, active_agents: 2 });
  mocks.billing.mockResolvedValue({
    credit_balance: 42,
    current_period_usage: 18,
    subscription: { status: "active" },
  });
});
afterEach(cleanup);

describe("workspace dashboard", () => {
  it("shows selected-workspace call insights and recent call records to regular users", async () => {
    mount();
    await screen.findAllByText("Fixture receptionist");

    expect(screen.getByRole("heading", { name: "Test workspace" })).toBeTruthy();
    expect(screen.getByRole("region", { name: "Dashboard filters" })).toBeTruthy();
    expect(screen.getByRole("region", { name: "Call performance" }).querySelector("#dashboard-period")).toBeNull();
    expect(screen.getByText("Call performance")).toBeTruthy();
    expect(screen.getByText("Peak call hours")).toBeTruthy();
    expect(screen.getByText(/Busiest: 14:00/)).toBeTruthy();
    expect(screen.getByText("Call outcomes")).toBeTruthy();
    expect(screen.getByText("Recent calls")).toBeTruthy();
    expect(screen.getAllByText("Fixture receptionist")).toHaveLength(2);
    expect(screen.getByText("Open call history")).toBeTruthy();
    expect(screen.getByText("Avg. call duration")).toBeTruthy();
    expect(screen.queryByText("Account capacity")).toBeNull();
    expect(screen.queryByRole("link", { name: "Create agent" })).toBeNull();
    expect(mocks.analytics).toHaveBeenCalledWith(
      "org-1",
      "last_30_days",
      undefined,
      "America/Phoenix",
    );
    expect(mocks.agentSummary).toHaveBeenCalledWith("org-1");
    expect(mocks.billing).not.toHaveBeenCalled();

    const [, listFilters] = mocks.callList.mock.calls.at(-1) as [string, Record<string, string | number>];
    expect(listFilters.page_size).toBe(6);
    expect(listFilters.status).toBeUndefined();
    expect(new Date(listFilters.date_to_exclusive).getTime()).toBeGreaterThan(new Date(listFilters.date_from).getTime());
    expect(screen.queryByText("Total Revenue")).toBeNull();
  });

  it("keeps platform admins in the selected workspace and adds a separate platform pulse", async () => {
    mocks.role = "platform_admin";
    mount();
    await screen.findAllByText("Fixture receptionist");
    await screen.findByText("Organizations with calls");

    expect(screen.getByRole("heading", { name: "Test workspace" })).toBeTruthy();
    expect(mocks.analytics).toHaveBeenCalledWith("org-1", "last_30_days", undefined, "America/Phoenix");
    expect(mocks.api).toHaveBeenCalledWith("/api/v1/calls/platform/analytics");
    expect(screen.getByText("Platform pulse")).toBeTruthy();
    expect(screen.getByRole("link", { name: /View platform overview/ })).toBeTruthy();
  });

  it("updates the call chart readout immediately as the pointer moves between days", async () => {
    mount();
    await screen.findAllByText("Fixture receptionist");

    const chart = screen.getByRole("group", {
      name: /Daily call volume chart/,
    });
    const markers = Array.from(chart.querySelectorAll("[data-chart-marker]"));
    const markerClasses = markers.map((marker) => marker.getAttribute("class"));
    expect(markers).toHaveLength(2);
    expect(markerClasses[0]).toContain("h-1.5 w-1.5");
    expect(markerClasses[0]).toContain("rounded-full");
    expect(markerClasses.every((className) => className === markerClasses[0])).toBe(
      true,
    );
    setChartBounds(chart, 100);

    fireEvent.pointerMove(chart, { pointerType: "mouse", clientX: 20 });
    expect(screen.getByRole("tooltip").getAttribute("aria-label")).toBe(
      "Sep 14, 2026, 8 calls",
    );

    fireEvent.pointerMove(chart, { pointerType: "mouse", clientX: 80 });
    expect(screen.getByRole("tooltip").getAttribute("aria-label")).toBe(
      "Sep 15, 2026, 12 calls",
    );
    expect(
      Array.from(chart.querySelectorAll("[data-chart-marker]")).map((marker) =>
        marker.getAttribute("class"),
      ),
    ).toEqual(markerClasses);
  });

  it("uses the same immediate readout for peak hours and call outcomes", async () => {
    mount();
    await screen.findAllByText("Fixture receptionist");

    const hours = screen.getByRole("group", {
      name: /Calls by hour in America\/Phoenix/,
    });
    expect(hours.querySelector("[title]")).toBeNull();
    setChartBounds(hours, 240, 96);
    fireEvent.pointerMove(hours, { pointerType: "mouse", clientX: 145 });
    expect(screen.getByRole("tooltip").getAttribute("aria-label")).toBe(
      "14:00–15:00, 4 calls",
    );

    fireEvent.pointerLeave(hours, { pointerType: "mouse" });
    const outcomes = screen.getByRole("group", {
      name: /Call outcomes by status/,
    });
    expect(outcomes.querySelector("[title]")).toBeNull();
    setChartBounds(outcomes, 200, 56);
    fireEvent.pointerMove(outcomes, { pointerType: "mouse", clientX: 150 });
    expect(screen.getByRole("tooltip").getAttribute("aria-label")).toBe(
      "Failed, 5 calls",
    );
  });

  it("lets keyboard users inspect call chart values one day at a time", async () => {
    mount();
    await screen.findAllByText("Fixture receptionist");

    const chart = screen.getByRole("group", {
      name: /Daily call volume chart/,
    });
    fireEvent.focus(chart);
    expect(screen.getByRole("tooltip").getAttribute("aria-label")).toBe(
      "Sep 14, 2026, 8 calls",
    );

    fireEvent.keyDown(chart, { key: "ArrowRight" });
    expect(screen.getByRole("tooltip").getAttribute("aria-label")).toBe(
      "Sep 15, 2026, 12 calls",
    );
  });

  it("shows callback management and billing capacity only to organization admins", async () => {
    mocks.role = "org_admin";
    mount();
    await screen.findByText("42");

    expect(screen.getByRole("link", { name: "Manage callbacks" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Create agent" })).toBeTruthy();
    expect(mocks.billing).toHaveBeenCalledWith("org-1");
    const followUp = screen.getByText("Follow-up requests").closest("section");
    const accountCapacity = screen.getByText("Account capacity").closest("section");
    expect(followUp?.parentElement?.className ?? "").toContain("xl:col-span-8");
    expect(accountCapacity?.parentElement?.className ?? "").toContain("xl:col-span-4");
  });

  it("changes the period and status filter for both metrics and the recent-call preview", async () => {
    const user = userEvent.setup();
    mount();
    await screen.findAllByText("Fixture receptionist");

    const periodFilter = screen.getByLabelText("Call reporting period") as HTMLSelectElement;
    expect(Array.from(periodFilter.options).map((option) => option.textContent)).toEqual([
      "Today",
      "Yesterday",
      "Last 7 days",
      "Last 15 days",
      "Last 30 days",
    ]);

    await user.selectOptions(periodFilter, "last_7_days");
    await waitFor(() =>
      expect(mocks.analytics).toHaveBeenCalledWith("org-1", "last_7_days", undefined, "America/Phoenix"),
    );

    await user.selectOptions(screen.getByLabelText("Call status filter"), "failed");
    expect(screen.getByLabelText("Call status filter")).toHaveProperty("value", "failed");
    await waitFor(() =>
      expect(mocks.analytics).toHaveBeenCalledWith("org-1", "last_7_days", "failed", "America/Phoenix"),
    );
    await waitFor(() => {
      const [, filters] = mocks.callList.mock.calls.at(-1) as [string, Record<string, string | number>];
      expect(filters.status).toBe("failed");
      expect(filters.page_size).toBe(6);
      expect(filters.date_to).toBeUndefined();
      expect(Number(new Date(filters.date_to_exclusive)) - Number(new Date(filters.date_from))).toBe(7 * 24 * 60 * 60 * 1000);
    });

    await user.selectOptions(periodFilter, "yesterday");
    await waitFor(() =>
      expect(mocks.analytics).toHaveBeenCalledWith("org-1", "yesterday", "failed", "America/Phoenix"),
    );
    await waitFor(() => {
      const [, filters] = mocks.callList.mock.calls.at(-1) as [string, Record<string, string | number>];
      expect(filters.status).toBe("failed");
      expect(filters.date_to).toBeUndefined();
      expect(Number(new Date(filters.date_to_exclusive)) - Number(new Date(filters.date_from))).toBe(24 * 60 * 60 * 1000);
    });
  });

  it("does not request a workspace report when no organization is selected", async () => {
    mocks.role = "platform_admin";
    mocks.orgId = "";
    mount();
    await screen.findByText("Organizations with calls");

    expect(screen.getByRole("heading", { name: "Choose a workspace" })).toBeTruthy();
    expect(mocks.analytics).not.toHaveBeenCalled();
    expect(mocks.api).toHaveBeenCalledWith("/api/v1/calls/platform/analytics");
    expect(mocks.agentSummary).not.toHaveBeenCalled();
    expect(mocks.billing).not.toHaveBeenCalled();
  });

  it("shows an analytics error without inventing zero totals or hiding recent calls", async () => {
    mocks.analytics.mockRejectedValue(new Error("offline"));
    mount();
    await screen.findByRole("alert");

    expect(screen.getByText("Recent calls")).toBeTruthy();
    expect(screen.getByText("Open call history")).toBeTruthy();
    expect(screen.queryByText("Avg. call duration")).toBeNull();
    expect(screen.getByRole("button", { name: "Try again" })).toBeTruthy();
  });

  it("explains a genuinely empty reporting period", async () => {
    mocks.analytics.mockResolvedValue({
      ...analyticsData,
      total_calls_month: 0,
      total_calls_week: 0,
      selected_total_calls: 0,
      selected_average_duration_seconds: null,
      calls_by_status: [],
      calls_by_agent: [],
      calls_by_day: [],
      calls_by_hour: Array.from({ length: 24 }, (_, hour) => ({ hour, calls: 0 })),
    });
    mount();

    await screen.findByText("No calls in this period");
    expect(screen.getAllByText("No calls match these filters.")).toHaveLength(2);
    expect(screen.queryByText("Busiest agents")).toBeNull();
  });

  it("uses the new organization scope and clears a prior organization's status", async () => {
    const { rerender, client } = mount();
    await screen.findAllByText("Fixture receptionist");
    fireEvent.change(screen.getByLabelText("Call status filter"), { target: { value: "failed" } });
    await waitFor(() => expect(mocks.analytics).toHaveBeenCalledWith("org-1", "last_30_days", "failed", "America/Phoenix"));

    mocks.orgId = "org-2";
    rerender(
      <QueryClientProvider client={client}>
        <DashboardPage />
      </QueryClientProvider>,
    );
    await waitFor(() => expect(mocks.analytics).toHaveBeenCalledWith("org-2", "last_30_days", undefined, "America/Phoenix"));
    expect(screen.getByLabelText("Call status filter")).toHaveProperty("value", "");
  });
});
