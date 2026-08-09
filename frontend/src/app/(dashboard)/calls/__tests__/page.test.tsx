import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiRequestError } from "@/lib/api/client";

const mockUseOrganization = vi.fn();
const mockUseOrganizationById = vi.fn();
const mockUseMyAgents = vi.fn();
const mockUseCallLogs = vi.fn();
const mockUseUserPermissions = vi.fn();
const mockRefetch = vi.fn();
const mockDownloadRecording = vi.hoisted(() => vi.fn());

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("@/contexts/organization-context", () => ({
  useOrganization: () => mockUseOrganization(),
}));

vi.mock("@/hooks/use-organization-by-id", () => ({
  useOrganizationById: (...args: unknown[]) => mockUseOrganizationById(...args),
}));

vi.mock("@/hooks/use-agent-queries", () => ({
  useMyAgents: () => mockUseMyAgents(),
}));

vi.mock("@/hooks/use-call-logs", () => ({
  useCallLogs: (...args: unknown[]) => mockUseCallLogs(...args),
}));

vi.mock("@/hooks/use-user-permissions", () => ({
  useUserPermissions: () => mockUseUserPermissions(),
}));

vi.mock("@/services/call-log-service", () => ({
  callLogService: { downloadRecording: mockDownloadRecording },
}));

describe("CallsPage date filters", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockDownloadRecording.mockReset();

    const organization = { id: "org-1", name: "Acme", slug: "acme" };
    mockUseOrganization.mockReturnValue({
      currentOrganization: organization,
      setCurrentOrganization: vi.fn(),
    });
    mockUseOrganizationById.mockReturnValue({
      isValid: true,
      loading: false,
      organization,
    });
    mockUseMyAgents.mockReturnValue({ data: [] });
    mockUseUserPermissions.mockReturnValue({
      isOrgAdmin: true,
      isPlatformAdmin: false,
    });
    mockUseCallLogs.mockReturnValue({
      data: { items: [], total: 0, page: 1, page_size: 25, total_pages: 1 },
      isLoading: false,
      isFetching: false,
      error: null,
      refetch: mockRefetch,
    });
  });

  it("prevents the To date from preceding From and keeps the range valid", async () => {
    const { default: CallsPage } = await import("../page");

    render(<CallsPage />);

    const fromDate = screen.getByLabelText("From");
    const toDate = screen.getByLabelText("To");

    fireEvent.change(toDate, { target: { value: "2026-08-09" } });
    fireEvent.change(fromDate, { target: { value: "2026-08-10" } });

    expect(toDate).toHaveAttribute("min", "2026-08-10");
    expect(toDate).toHaveValue("");

    fireEvent.change(toDate, { target: { value: "2026-08-11" } });
    expect(toDate).toHaveValue("2026-08-11");
  });

  it("allows an admin to refresh the call list after an external call completes", async () => {
    const { default: CallsPage } = await import("../page");

    render(<CallsPage />);

    fireEvent.click(screen.getByRole("button", { name: "Refresh" }));

    expect(mockRefetch).toHaveBeenCalledOnce();
  });

  it("shows recording retention, privacy, and consent guidance to admins", async () => {
    const { default: CallsPage } = await import("../page");

    render(<CallsPage />);

    expect(
      screen.getByText(
        /recordings are private and available only to organization and platform admins/i,
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/retained according to the configured policy/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/ensure callers are notified and consent requirements/i),
    ).toBeInTheDocument();
  });

  it("hides a listen action after the recording object is missing", async () => {
    mockUseCallLogs.mockReturnValue({
      data: {
        items: [
          {
            id: "call-1",
            call_sid: "sid-1",
            organization_id: "org-1",
            agent_id: null,
            caller_number: "+15555550100",
            called_number: "+15555550101",
            status: "completed",
            duration: 30,
            credits_consumed: 5,
            credit_transaction_id: null,
            recording_available: true,
            started_at: "2026-08-09T10:00:00Z",
            ended_at: "2026-08-09T10:00:30Z",
            created_at: "2026-08-09T10:00:00Z",
            updated_at: "2026-08-09T10:00:30Z",
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
      refetch: mockRefetch,
    });
    mockDownloadRecording.mockRejectedValue(
      new ApiRequestError("Recording is no longer available", 410),
    );

    const { default: CallsPage } = await import("../page");

    render(<CallsPage />);

    fireEvent.click(
      screen.getAllByRole("button", {
        name: /Listen to recording for call call-1/i,
      })[0],
    );

    await waitFor(() => {
      expect(
        screen.queryByRole("button", {
          name: /Listen to recording for call call-1/i,
        }),
      ).not.toBeInTheDocument();
    });
    expect(
      await screen.findByText(/recording is no longer available/i),
    ).toBeInTheDocument();
  });
});
