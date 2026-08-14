import React from "react";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mockUseCallLogs = vi.fn();

vi.mock("@/hooks/use-call-logs", () => ({
  useCallLogs: (...args: unknown[]) => mockUseCallLogs(...args),
}));

vi.mock("@/services/call-log-service", () => ({
  callLogService: { downloadRecording: vi.fn() },
}));

describe("AgentCallRecordings", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseCallLogs.mockReturnValue({
      data: {
        items: [],
        total: 0,
        page: 1,
        page_size: 25,
        total_pages: 1,
      },
      isLoading: false,
      isFetching: false,
      error: null,
      refetch: vi.fn(),
    });
  });

  it("loads all calls for the selected agent", async () => {
    const { AgentCallRecordings } = await import("../agent-call-recordings");

    render(
      <AgentCallRecordings
        organizationId="org-1"
        agentId="agent-1"
        agentName="Reception Agent"
      />,
    );

    expect(mockUseCallLogs).toHaveBeenCalledWith("org-1", {
      agent_id: "agent-1",
      page: 1,
      page_size: 25,
    });
    expect(screen.getByText("No calls yet")).toBeInTheDocument();
  });

  it("shows call duration and credits used for each recording", async () => {
    mockUseCallLogs.mockReturnValue({
      data: {
        items: [
          {
            id: "call-1",
            caller_number: "+15555550100",
            created_at: "2026-08-14T10:00:00Z",
            duration: 125,
            credits_consumed: 12,
            recording_available: true,
          },
        ],
        total: 1,
        page: 1,
        page_size: 25,
        total_pages: 1,
      },
      isLoading: false,
      isFetching: false,
      error: null,
      refetch: vi.fn(),
    });
    const { AgentCallRecordings } = await import("../agent-call-recordings");

    render(
      <AgentCallRecordings
        organizationId="org-1"
        agentId="agent-1"
        agentName="Reception Agent"
      />,
    );

    expect(screen.getAllByText("2m 5s").length).toBeGreaterThan(0);
    expect(screen.getAllByText("12").length).toBeGreaterThan(0);
  });
});
