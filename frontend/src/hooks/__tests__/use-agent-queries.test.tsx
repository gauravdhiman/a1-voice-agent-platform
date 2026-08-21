import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

const {
  getAgentTools,
  getAgentSystemPrompt,
  getPlatformTools,
  getMyAgents,
  createAgent,
  updateAgent,
  deleteAgent,
} = vi.hoisted(() => ({
  getAgentTools: vi.fn(),
  getAgentSystemPrompt: vi.fn(),
  getPlatformTools: vi.fn(),
  getMyAgents: vi.fn(),
  createAgent: vi.fn(),
  updateAgent: vi.fn(),
  deleteAgent: vi.fn(),
}));

vi.mock("@/services/agent-service", () => ({
  agentService: {
    getAgentTools,
    getAgentSystemPrompt,
    getPlatformTools,
    getMyAgents,
    createAgent,
    updateAgent,
    deleteAgent,
  },
}));

import {
  useAgentSystemPrompt,
  useAgentTools,
  useCreateAgent,
  useDeleteAgent,
  useMyAgents,
  usePlatformTools,
  useUpdateAgent,
  agentQueryKeys,
} from "../use-agent-queries";

function createWrapper(queryClient?: QueryClient) {
  const client = queryClient ?? new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
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

  it("does not fetch all organizations when the all-agent query is disabled", () => {
    renderHook(() => useMyAgents(false), {
      wrapper: createWrapper(),
    });

    expect(getMyAgents).not.toHaveBeenCalled();
  });

  it("invalidates organization agent lists after creating an agent", async () => {
    createAgent.mockResolvedValueOnce({ id: "agent-1" });
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const invalidateQueries = vi.spyOn(queryClient, "invalidateQueries");

    const { result } = renderHook(() => useCreateAgent(), {
      wrapper: createWrapper(queryClient),
    });

    await act(async () => {
      await result.current.mutateAsync({
        organization_id: "org-1",
        name: "New agent",
      } as never);
    });

    expect(invalidateQueries).toHaveBeenCalledWith({
      queryKey: agentQueryKeys.organizations(),
    });
  });

  it("invalidates organization agent lists after updating an agent", async () => {
    updateAgent.mockResolvedValueOnce({ id: "agent-1" });
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const invalidateQueries = vi.spyOn(queryClient, "invalidateQueries");

    const { result } = renderHook(() => useUpdateAgent(), {
      wrapper: createWrapper(queryClient),
    });

    await act(async () => {
      await result.current.mutateAsync({
        agentId: "agent-1",
        data: { name: "Updated agent" },
      });
    });

    expect(invalidateQueries).toHaveBeenCalledWith({
      queryKey: agentQueryKeys.organizations(),
    });
  });

  it("invalidates organization agent lists after deleting an agent", async () => {
    deleteAgent.mockResolvedValueOnce(undefined);
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const invalidateQueries = vi.spyOn(queryClient, "invalidateQueries");

    const { result } = renderHook(() => useDeleteAgent(), {
      wrapper: createWrapper(queryClient),
    });

    await act(async () => {
      await result.current.mutateAsync("agent-1");
    });

    expect(invalidateQueries).toHaveBeenCalledWith({
      queryKey: agentQueryKeys.organizations(),
    });
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
