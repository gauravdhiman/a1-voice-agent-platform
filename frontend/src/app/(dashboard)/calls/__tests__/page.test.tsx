import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mockUseOrganization = vi.fn();
const mockUseOrganizationById = vi.fn();
const mockUseMyAgents = vi.fn();
const mockUseCallLogs = vi.fn();
const mockRefetch = vi.fn();

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

describe("CallsPage date filters", () => {
  beforeEach(() => {
    vi.clearAllMocks();

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
});
