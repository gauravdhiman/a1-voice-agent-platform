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

  it("loads only recorded calls for the selected agent", async () => {
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
      recording_only: true,
      page: 1,
      page_size: 25,
    });
    expect(screen.getByText("No recordings yet")).toBeInTheDocument();
  });
});
