import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { CallLogsResponse } from "@/services/call-log-service";

vi.mock("@/services/call-log-service", async () => {
  const actual = await vi.importActual<typeof import("@/services/call-log-service")>(
    "@/services/call-log-service",
  );
  return {
    ...actual,
    callLogService: { downloadRecording: vi.fn() },
  };
});

const CALLS: CallLogsResponse = {
  items: [
    {
      id: "call-1",
      call_sid: "sid-1",
      organization_id: "org-1",
      agent_id: "agent-1",
      caller_number: "+15555550100",
      called_number: "+15555550101",
      source_type: "web_embed",
      source_url: "https://example.com/support",
      source_domain: "example.com",
      status: "completed",
      duration: 125,
      credits_consumed: 12,
      credit_transaction_id: null,
      recording_available: true,
      started_at: "2026-08-14T10:00:00Z",
      ended_at: "2026-08-14T10:02:05Z",
      created_at: "2026-08-14T10:00:00Z",
      updated_at: "2026-08-14T10:02:05Z",
    },
  ],
  total: 1,
  page: 1,
  page_size: 25,
  total_pages: 1,
};

const FAILED_CALLS: CallLogsResponse = {
  ...CALLS,
  items: [
    {
      ...CALLS.items[0],
      status: "failed",
      failure_code: "model_reasoning_required",
      failure_message:
        "The selected language model rejected the configured reasoning settings.",
    },
  ],
};

describe("CallLogList", () => {
  it("renders shared call fields and can hide the agent column", async () => {
    const { CallLogList } = await import("../call-log-list");

    render(
      <CallLogList
        data={CALLS}
        isLoading={false}
        isFetching={false}
        error={null}
        onRefresh={vi.fn()}
        onPageChange={vi.fn()}
        showAgentColumn={false}
        canViewRecordings
      />,
    );

    expect(screen.getAllByText("+15555550100").length).toBeGreaterThan(0);
    expect(screen.getAllByText("2m 5s").length).toBeGreaterThan(0);
    expect(screen.getAllByText("12").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Web embed").length).toBeGreaterThan(0);
    expect(screen.getAllByText("example.com/support").length).toBeGreaterThan(0);
    expect(
      screen.queryByRole("columnheader", { name: "Agent" }),
    ).not.toBeInTheDocument();
    expect(
      screen.getAllByRole("button", {
        name: /Listen to recording for call call-1/i,
      }).length,
    ).toBeGreaterThan(0);
  });

  it("shows the safe runtime failure classification in the call log", async () => {
    const { CallLogList } = await import("../call-log-list");

    render(
      <CallLogList
        data={FAILED_CALLS}
        isLoading={false}
        isFetching={false}
        error={null}
        onRefresh={vi.fn()}
        onPageChange={vi.fn()}
        showAgentColumn={false}
        canViewRecordings={false}
      />,
    );

    expect(
      screen.getAllByText("Issue: Model Reasoning Required").length,
    ).toBeGreaterThan(0);
    expect(
      screen.getAllByText(
        "The selected language model rejected the configured reasoning settings.",
      ).length,
    ).toBeGreaterThan(0);
  });
});
