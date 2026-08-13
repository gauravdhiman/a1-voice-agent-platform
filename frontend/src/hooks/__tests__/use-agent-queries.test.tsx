import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

const { getAgentTools, getAgentSystemPrompt, getPlatformTools } = vi.hoisted(() => ({
  getAgentTools: vi.fn(),
  getAgentSystemPrompt: vi.fn(),
  getPlatformTools: vi.fn(),
}));

vi.mock("@/services/agent-service", () => ({
  agentService: {
    getAgentTools,
    getAgentSystemPrompt,
    getPlatformTools,
  },
}));

import {
  useAgentSystemPrompt,
  useAgentTools,
  usePlatformTools,
} from "../use-agent-queries";

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

describe("agent detail query loading", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("does not fetch agent tools until the tools tab is opened", () => {
    renderHook(() => useAgentTools("agent-1", false), {
      wrapper: createWrapper(),
    });

    expect(getAgentTools).not.toHaveBeenCalled();
  });

  it("does not generate the system prompt preview until requested", () => {
    renderHook(() => useAgentSystemPrompt("agent-1", false), {
      wrapper: createWrapper(),
    });

    expect(getAgentSystemPrompt).not.toHaveBeenCalled();
  });

  it("does not fetch platform tools until the tools tab is opened", () => {
    renderHook(() => usePlatformTools(true, { enabled: false }), {
      wrapper: createWrapper(),
    });

    expect(getPlatformTools).not.toHaveBeenCalled();
  });

  it("passes draft visibility to the platform tools request when enabled", async () => {
    getPlatformTools.mockResolvedValueOnce([]);

    renderHook(() => usePlatformTools(false, { includeDrafts: true }), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(getPlatformTools).toHaveBeenCalledWith(false, {
        includeDrafts: true,
      });
    });
  });
});
