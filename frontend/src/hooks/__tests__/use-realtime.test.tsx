import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const subscribe = vi.fn();
const unsubscribe = vi.fn();

vi.mock("@/lib/realtime", () => ({
  getRealtimeService: () => ({ subscribe, unsubscribe }),
}));

import { useRealtime } from "../use-realtime";

function createWrapper() {
  const queryClient = new QueryClient();
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

describe("useRealtime", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("does not resubscribe when the caller recreates an equivalent table list", () => {
    const { rerender, unmount } = renderHook(
      ({ tables }: { tables: string[] }) =>
        useRealtime("agent-1", { tables }),
      {
        initialProps: { tables: ["agent_tools", "voice_agents"] },
        wrapper: createWrapper(),
      },
    );

    rerender({ tables: ["agent_tools", "voice_agents"] });

    expect(subscribe).toHaveBeenCalledTimes(1);
    expect(unsubscribe).not.toHaveBeenCalled();

    unmount();
    expect(unsubscribe).toHaveBeenCalledTimes(1);
  });

  it("forwards insert, update, and delete callbacks to the caller", () => {
    const onChange = vi.fn();
    renderHook(
      () =>
        useRealtime("agent-1", {
          tables: ["agent_tools", "voice_agents"],
          onChange,
        }),
      { wrapper: createWrapper() },
    );

    const subscription = subscribe.mock.calls[0][0];
    subscription.onInsert({ table: "agent_tools", record: {} });
    subscription.onUpdate({ table: "voice_agents", record: {} });
    subscription.onDelete({ table: "other", record: {} });

    expect(onChange).toHaveBeenCalledTimes(3);
  });

  it("invalidates queries for each configured realtime table on refetch", () => {
    const queryClient = new QueryClient();
    const invalidateQueries = vi.spyOn(queryClient, "invalidateQueries");
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
    const { result } = renderHook(
      () => useRealtime("agent-1", { tables: ["agent_tools", "voice_agents"] }),
      { wrapper },
    );

    result.current.refetch();

    expect(invalidateQueries).toHaveBeenCalledTimes(2);
    const firstPredicate = invalidateQueries.mock.calls[0][0]?.predicate;
    expect(firstPredicate?.({ queryKey: ["agent_tools"] } as never)).toBe(true);
    expect(firstPredicate?.({ queryKey: ["unrelated"] } as never)).toBe(false);
  });
});
