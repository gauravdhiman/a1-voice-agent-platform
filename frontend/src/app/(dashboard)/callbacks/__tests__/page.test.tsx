import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { listMock, mutateMock, permissions } = vi.hoisted(() => ({
  listMock: vi.fn(),
  mutateMock: vi.fn(),
  permissions: { isOrgAdmin: true, isPlatformAdmin: false },
}));

vi.mock("@/contexts/organization-context", () => ({
  useOrganization: () => ({ currentOrganization: { id: "org-1" } }),
}));

vi.mock("@/hooks/use-user-permissions", () => ({
  useUserPermissions: () => permissions,
}));

vi.mock("@/hooks/use-escalations", () => ({
  useEscalations: (...args: unknown[]) => listMock(...args),
  useMarkEscalationStatus: () => ({
    mutate: mutateMock,
    isPending: false,
  }),
}));

import CallbacksPage from "../page";
import type { CallbackEscalation } from "@/services/callback-service";

function row(overrides: Partial<CallbackEscalation> = {}): CallbackEscalation {
  return {
    id: "esc-1",
    organization_id: "org-1",
    agent_id: null,
    session_id: null,
    caller_phone: "+14805550100",
    caller_name: null,
    reason: "Water heater is leaking.",
    urgency: "normal",
    status: "new",
    notified: true,
    created_at: "2026-09-04T00:00:00+00:00",
    acknowledged_at: null,
    ...overrides,
  };
}

describe("CallbacksPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    permissions.isOrgAdmin = true;
    permissions.isPlatformAdmin = false;
    listMock.mockReturnValue({
      data: [row()],
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    });
  });

  it("lists callback rows with acknowledge and resolve actions", async () => {
    const user = userEvent.setup();
    render(<CallbacksPage />);

    expect(screen.getByText("+14805550100")).not.toBeNull();
    expect(screen.getByText("Water heater is leaking.")).not.toBeNull();

    await user.click(screen.getByRole("button", { name: "Acknowledge" }));
    expect(mutateMock).toHaveBeenCalledWith({
      escalationId: "esc-1",
      status: "acknowledged",
    });
  });

  it("hides actions on resolved rows", () => {
    listMock.mockReturnValue({
      data: [row({ id: "esc-2", status: "resolved" })],
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    });
    render(<CallbacksPage />);

    expect(screen.queryByRole("button", { name: "Acknowledge" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Mark resolved" })).toBeNull();
  });

  it("explains the empty queue", () => {
    listMock.mockReturnValue({
      data: [],
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    });
    render(<CallbacksPage />);

    expect(screen.getByText(/no callback requests yet/i)).not.toBeNull();
    expect(
      screen.queryByRole("link", { name: "Platform Interest" }),
    ).toBeNull();
  });

  it("directs platform admins to the interest queue for demo submissions", () => {
    permissions.isOrgAdmin = false;
    permissions.isPlatformAdmin = true;
    render(<CallbacksPage />);

    const interestLink = screen.getByRole("link", {
      name: "Platform Interest",
    });
    expect(interestLink.getAttribute("href")).toBe("/platform/interest");
    expect(
      screen.getByText(/demo and request-form submissions are tracked/i),
    ).not.toBeNull();
  });
});
