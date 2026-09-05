import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  useOrganizationTools,
  useSetOrganizationToolVisibility,
} from "@/hooks/use-agent-queries";
import { OrganizationToolsManager } from "@/components/tools/organization-tools-manager";

vi.mock("@/hooks/use-agent-queries", () => ({
  useOrganizationTools: vi.fn(),
  useSetOrganizationToolVisibility: vi.fn(),
}));

const tool = {
  id: "tool-1",
  name: "google_calendar",
  description: "Calendar access",
  config_schema: null,
  tool_functions_schema: null,
  is_active: true,
  is_published: true,
  is_visible: false,
  requires_auth: false,
  auth_type: null,
  auth_config: null,
  created_at: "2024-01-01T00:00:00Z",
  updated_at: "2024-01-01T00:00:00Z",
} as const;

describe("OrganizationToolsManager", () => {
  const mutate = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useOrganizationTools).mockReturnValue({
      data: [tool],
      isLoading: false,
      isError: false,
    } as never);
    vi.mocked(useSetOrganizationToolVisibility).mockReturnValue({
      mutate,
    } as never);
  });

  it("shows hidden status and lets an organization admin restore a tool", () => {
    render(<OrganizationToolsManager orgId="org-1" canEdit />);

    expect(screen.getByText("Hidden from new connections")).toBeInTheDocument();
    const toggle = screen.getByRole("switch", { name: "Show google calendar" });

    fireEvent.click(toggle);

    expect(mutate).toHaveBeenCalledWith(
      {
        organizationId: "org-1",
        toolId: "tool-1",
        isVisible: true,
      },
      expect.objectContaining({ onSettled: expect.any(Function) }),
    );
  });

  it("disables the visibility control for non-admin viewers", () => {
    render(<OrganizationToolsManager orgId="org-1" canEdit={false} />);

    expect(
      screen.getByRole("switch", { name: "Show google calendar" }),
    ).toBeDisabled();
  });
});
