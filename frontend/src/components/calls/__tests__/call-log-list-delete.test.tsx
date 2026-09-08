import React from "react";
import {
  render,
  screen,
  waitFor,
  fireEvent,
} from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import type { CallLogsResponse } from "@/services/call-log-service";

const deleteRecordingMock = vi.fn();
const deleteRecordingsMock = vi.fn();

vi.mock("@/services/call-log-service", async () => {
  const actual = await vi.importActual<typeof import("@/services/call-log-service")>(
    "@/services/call-log-service",
  );
  return {
    ...actual,
    callLogService: {
      downloadRecording: vi.fn(),
      deleteRecording: deleteRecordingMock,
      deleteRecordings: deleteRecordingsMock,
    },
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
      source_type: "phone",
      source_url: null,
      source_domain: null,
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
    {
      id: "call-2",
      call_sid: "sid-2",
      organization_id: "org-1",
      agent_id: "agent-1",
      caller_number: "+15555550100",
      called_number: "+15555550101",
      source_type: "phone",
      source_url: null,
      source_domain: null,
      status: "completed",
      duration: 60,
      credits_consumed: 6,
      credit_transaction_id: null,
      recording_available: true,
      started_at: "2026-08-15T10:00:00Z",
      ended_at: "2026-08-15T10:01:00Z",
      created_at: "2026-08-15T10:00:00Z",
      updated_at: "2026-08-15T10:01:00Z",
    },
  ],
  total: 2,
  page: 1,
  page_size: 25,
  total_pages: 1,
};

async function renderList(overrides: Record<string, unknown> = {}) {
  // Imported inside the helper so the vi.mock factory above is guaranteed
  // to be registered before the component module loads.
  const imported = await import("../call-log-list");
  const CallLogList = imported.CallLogList;
  return render(
    <CallLogList
      data={CALLS}
      isLoading={false}
      isFetching={false}
      error={null}
      onRefresh={vi.fn()}
      onPageChange={vi.fn()}
      canViewRecordings
      {...overrides}
    />,
  );
}

describe("CallLogList recording deletion", () => {
  beforeEach(() => {
    deleteRecordingMock.mockReset();
    deleteRecordingsMock.mockReset();
  });

  it("hides delete affordances when canDeleteRecordings is false", async () => {
    await renderList();
    expect(
      screen.queryByRole("button", { name: /Delete recording for call/i }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("checkbox", { name: /Select all calls/i }),
    ).not.toBeInTheDocument();
  });

  it("shows per-row delete buttons and select-all checkbox for admins", async () => {
    await renderList({ canDeleteRecordings: true });
    // Desktop table and mobile cards both render; two calls → four buttons.
    expect(
      screen.getAllByRole("button", { name: /Delete recording for call/i })
        .length,
    ).toBe(4);
    expect(
      screen.getByRole("checkbox", { name: /Select all calls/i }),
    ).toBeInTheDocument();
  });

  it("single delete confirms without typing and calls the API once", async () => {
    deleteRecordingMock.mockResolvedValue(undefined);
    const onRefresh = vi.fn();
    await renderList({ canDeleteRecordings: true, onRefresh });
    fireEvent.click(
      screen
        .getAllByRole("button", {
          name: /Delete recording for call call-1/i,
        })
        .at(0) as HTMLElement,
    );
    expect(screen.getByText(/audio file will be permanently deleted/i))
      .toBeInTheDocument();

    // No typed confirmation required for single delete.
    fireEvent.click(screen.getByRole("button", { name: "Delete recording" }));

    await waitFor(() =>
      expect(deleteRecordingMock).toHaveBeenCalledWith("call-1"),
    );
    expect(onRefresh).toHaveBeenCalled();
  });

  it("bulk delete requires typing the exact selection count", async () => {
    deleteRecordingsMock.mockResolvedValue({
      success: true,
      data: {
        items: [
          { call_log_id: "call-1", status: "deleted" },
          { call_log_id: "call-2", status: "deleted" },
        ],
        deleted_count: 2,
      },
    });
    await renderList({ canDeleteRecordings: true, organizationId: "org-1" });

    // Select both rows via the header checkbox.
    fireEvent.click(
      screen.getByRole("checkbox", { name: /Select all calls/i }),
    );

    // Bulk bar appears with the count.
    expect(screen.getByText(/2 recordings selected/i)).toBeInTheDocument();
    fireEvent.click(
      screen.getByRole("button", { name: /Delete recordings$/i }),
    );

    const confirmButton = screen.getByRole("button", {
      name: /Delete 2 recordings/i,
    });
    expect(confirmButton).toBeDisabled();

    // Wrong number does not enable the button.
    fireEvent.change(
      screen.getByLabelText(/Type .* to confirm:/i),
      { target: { value: "3" } },
    );
    expect(
      screen.getByRole("button", { name: /Delete 2 recordings/i }),
    ).toBeDisabled();

    // Exact count enables it.
    fireEvent.change(
      screen.getByLabelText(/Type .* to confirm:/i),
      { target: { value: "2" } },
    );
    fireEvent.click(
      screen.getByRole("button", { name: /Delete 2 recordings/i }),
    );

    await waitFor(() =>
      expect(deleteRecordingsMock).toHaveBeenCalledWith(
        "org-1",
        ["call-1", "call-2"],
      ),
    );
  });

  it("surfaces partial batch failure counts in the bulk dialog error area", async () => {
    deleteRecordingsMock.mockResolvedValue({
      success: true,
      data: {
        items: [
          { call_log_id: "call-1", status: "deleted" },
          { call_log_id: "call-2", status: "failed" },
        ],
        deleted_count: 1,
      },
    });
    await renderList({ canDeleteRecordings: true, organizationId: "org-1" });

    fireEvent.click(
      screen.getByRole("checkbox", { name: /Select all calls/i }),
    );
    fireEvent.click(screen.getByRole("button", { name: /Delete recordings$/i }));
    fireEvent.change(screen.getByLabelText(/Type .* to confirm:/i), {
      target: { value: "2" },
    });
    fireEvent.click(
      screen.getByRole("button", { name: /Delete 2 recordings/i }),
    );

    await waitFor(() =>
      expect(screen.getByText(/1 deleted, 1 could not be removed\./i))
        .toBeInTheDocument(),
    );
  });
});
