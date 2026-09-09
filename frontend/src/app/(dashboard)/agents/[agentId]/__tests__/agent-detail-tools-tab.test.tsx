import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  useAgentTools: vi.fn(),
  usePlatformTools: vi.fn(),
  useConfigureAgentTool: vi.fn(),
  useDeleteAgentTool: vi.fn(),
  useLogoutAgentTool: vi.fn(),
  useStartOAuth: vi.fn(),
  useToggleFunction: vi.fn(),
  useUpdateAgentTool: vi.fn(),
  getOrganizationEntitlements: vi.fn(),
  setApiKey: vi.fn(),
}));

vi.mock("next/dynamic", () => ({
  default: () => () => null,
}));

vi.mock("@/hooks/use-realtime", () => ({
  useRealtime: vi.fn(),
}));

vi.mock("@/hooks/use-agent-queries", () => ({
  useAgentTools: mocks.useAgentTools,
  usePlatformTools: mocks.usePlatformTools,
  useConfigureAgentTool: mocks.useConfigureAgentTool,
  useDeleteAgentTool: mocks.useDeleteAgentTool,
  useLogoutAgentTool: mocks.useLogoutAgentTool,
  useStartOAuth: mocks.useStartOAuth,
  useToggleFunction: mocks.useToggleFunction,
  useUpdateAgentTool: mocks.useUpdateAgentTool,
}));

vi.mock("@/services/agent-service", () => ({
  agentService: {
    setApiKey: mocks.setApiKey,
  },
}));

vi.mock("@/services/billing-service", () => ({
  billingService: {
    getOrganizationEntitlements: mocks.getOrganizationEntitlements,
  },
}));

vi.mock("@/components/tools/tool-card", () => ({
  ToolCard: ({
    tool,
    onClick,
  }: {
    tool: { name: string };
    onClick: () => void;
  }) => (
    <button type="button" onClick={onClick}>
      {tool.name}
    </button>
  ),
}));

import { AgentDetailToolsTab } from "../agent-detail-tools-tab";
import type { AgentTool, PlatformTool, VoiceAgent } from "@/types/agent";

const TOOL: PlatformTool = {
  id: "tool-1",
  name: "Calendar",
  description: "Manage calendar appointments.",
  tool_source: "legacy",
  auth_type: null,
  requires_auth: false,
  is_premium: false,
} as PlatformTool;

const AGENT: VoiceAgent = {
  id: "agent-1",
  organization_id: "org-1",
  name: "Test Agent",
} as VoiceAgent;

function makeMutation() {
  return {
    mutateAsync: vi.fn().mockResolvedValue(undefined),
    isPending: false,
  };
}

function renderToolsTab() {
  return render(
    <AgentDetailToolsTab agent={AGENT} organization={null} canEdit />,
  );
}

describe("AgentDetailToolsTab", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.usePlatformTools.mockReturnValue({
      data: [TOOL],
      isLoading: false,
    });
    mocks.useAgentTools.mockReturnValue({
      data: [],
      refetch: vi.fn(),
    });
    mocks.useConfigureAgentTool.mockReturnValue(makeMutation());
    mocks.useDeleteAgentTool.mockReturnValue(makeMutation());
    mocks.useLogoutAgentTool.mockReturnValue(makeMutation());
    mocks.useStartOAuth.mockReturnValue(makeMutation());
    mocks.useToggleFunction.mockReturnValue(makeMutation());
    mocks.useUpdateAgentTool.mockReturnValue(makeMutation());
    mocks.getOrganizationEntitlements.mockReturnValue(new Promise(() => {}));
  });

  it("does not enter an update loop while agent tools are still loading", () => {
    mocks.useAgentTools.mockReturnValue({
      data: undefined,
      refetch: vi.fn(),
    });

    expect(() => renderToolsTab()).not.toThrow();
    expect(
      screen.getByRole("button", { name: "See all tools" }),
    ).toBeTruthy();
  });

  it("starts on Connected and lets the user browse all tools when none are connected", () => {
    renderToolsTab();

    expect(
      screen.getByRole("button", { name: "Connected" }).className,
    ).toContain("bg-primary");
    expect(
      screen.getByText("No tools are connected to this agent yet."),
    ).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "See all tools" }));

    expect(screen.getByRole("button", { name: "All" }).className).toContain(
      "bg-primary",
    );
    expect(screen.getByRole("button", { name: "Calendar" })).toBeTruthy();
  });

  it("shows connected tools in the initial view", () => {
    const agentTool: AgentTool = {
      id: "agent-tool-1",
      tool_id: TOOL.id,
      tool: TOOL,
    } as AgentTool;
    mocks.useAgentTools.mockReturnValue({
      data: [agentTool],
      refetch: vi.fn(),
    });

    renderToolsTab();

    expect(screen.getByRole("button", { name: "Calendar" })).toBeTruthy();
    expect(
      screen.queryByRole("button", { name: "See all tools" }),
    ).toBeNull();
  });
});
