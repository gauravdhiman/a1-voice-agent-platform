import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ToolCard } from "@/components/tools/tool-card";
import { AuthStatus, ConnectionStatus } from "@/types/agent";

vi.mock("@/hooks/use-live-time", () => ({
  useLiveTime: () => 1_700_000_000_000,
  formatTimeUntilExpiry: (_expiresAt: number | null) => null,
}));

const baseTool = {
  id: "tool-1",
  name: "google_calendar",
  description: "Calendar tool",
  tool_source: "legacy" as const,
  mcp_server_url: null,
};

function renderToolCard(props: Record<string, unknown> = {}) {
  return render(
    <ToolCard
      tool={baseTool}
      authStatus={AuthStatus.NOT_AUTHENTICATED}
      tokenExpiresAt={null}
      connectionStatus={ConnectionStatus.NOT_CONNECTED}
      onClick={() => {}}
      {...props}
    />,
  );
}

describe("ToolCard premium gating", () => {
  it("shows when an existing connection is hidden from the organization", () => {
    renderToolCard({
      connectionStatus: ConnectionStatus.CONNECTED_NO_AUTH,
      isConfigured: true,
      isHiddenForOrganization: true,
    });

    expect(screen.getByText("Hidden")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Hidden from Organization Tools — still connected to this agent.",
      ),
    ).toBeInTheDocument();
  });

  it("shows a red configuration-required state for an attached incomplete tool", () => {
    renderToolCard({
      connectionStatus: ConnectionStatus.CONFIGURATION_REQUIRED,
      isConfigured: true,
    });

    expect(screen.getByText("Configuration required")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Edit Configuration" }),
    ).toBeInTheDocument();
  });

  it("lists what is missing when the backend reports issues", () => {
    const { container } = renderToolCard({
      connectionStatus: ConnectionStatus.CONFIGURATION_REQUIRED,
      isConfigured: true,
      configurationIssues: ["spreadsheet destination is not set"],
    });

    expect(
      container.querySelector('[data-testid="tool-configuration-issues"]'),
    ).not.toBeNull();
    expect(screen.getByText("spreadsheet destination is not set")).not.toBeNull();
  });

  it("shows no issue list for a complete attachment", () => {
    const { container } = renderToolCard({
      connectionStatus: ConnectionStatus.CONNECTED_AUTH_VALID,
      isConfigured: true,
      configurationIssues: [],
    });

    expect(
      container.querySelector('[data-testid="tool-configuration-issues"]'),
    ).toBeNull();
  });

  it("renders a Premium badge for premium tools", () => {
    renderToolCard({ tool: { ...baseTool, is_premium: true } });

    expect(screen.getByText("Premium")).toBeInTheDocument();
    expect(screen.getByText("Connect")).toBeInTheDocument();
  });

  it("renders a locked Premium action when the plan blocks premium tools", () => {
    renderToolCard({
      tool: { ...baseTool, is_premium: true },
      premiumBlocked: true,
    });

    // The connect action is replaced with a locked upgrade hint.
    expect(screen.queryByText("Connect")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Premium/i })).toBeInTheDocument();
  });

  it("keeps the normal Connect action when the plan entitles premium tools", () => {
    renderToolCard({
      tool: { ...baseTool, is_premium: true },
      premiumBlocked: false,
    });

    expect(screen.getByRole("button", { name: "Connect" })).toBeInTheDocument();
  });

  it("shows no Premium badge for non-premium tools", () => {
    renderToolCard({ tool: { ...baseTool, is_premium: false } });

    expect(screen.queryByText("Premium")).not.toBeInTheDocument();
  });
});
