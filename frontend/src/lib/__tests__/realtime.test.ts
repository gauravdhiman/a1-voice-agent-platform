/**
 * Unit tests for Supabase Realtime subscription recovery.
 *
 * Covers reconnect decisions after CHANNEL_ERROR / TIMED_OUT (the failure
 * mode seen when a tab sits idle and the Realtime JWT or WebSocket dies).
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  getRealtimeService,
  realtimeReconnectDelayMs,
  resetRealtimeService,
  shouldReconnectRealtimeChannel,
} from "@/lib/realtime";

const subscribeCallbacks: Array<
  (status: string, err?: Error | null) => void
> = [];
const channelInstances: Array<{
  on: ReturnType<typeof vi.fn>;
  subscribe: ReturnType<typeof vi.fn>;
}> = [];

const removeChannel = vi.fn();
const setAuth = vi.fn().mockResolvedValue(undefined);
const getSession = vi.fn().mockResolvedValue({
  data: { session: { access_token: "fresh-token" } },
  error: null,
});
const channelFactory = vi.fn((_name?: string) => {
  const channel = {
    on: vi.fn().mockReturnThis(),
    subscribe: vi.fn((cb: (status: string, err?: Error | null) => void) => {
      subscribeCallbacks.push(cb);
      return channel;
    }),
  };
  channelInstances.push(channel);
  return channel;
});

vi.mock("@/lib/supabase", () => ({
  supabase: {
    channel: (name: string) => channelFactory(name),
    removeChannel: (channel: unknown) => removeChannel(channel),
    auth: {
      getSession: () => getSession(),
    },
    realtime: {
      setAuth: (token: string) => setAuth(token),
    },
  },
}));

describe("shouldReconnectRealtimeChannel", () => {
  it("reconnects on CHANNEL_ERROR and TIMED_OUT", () => {
    expect(shouldReconnectRealtimeChannel("CHANNEL_ERROR")).toBe(true);
    expect(shouldReconnectRealtimeChannel("TIMED_OUT")).toBe(true);
  });

  it("does not reconnect on SUBSCRIBED or CLOSED", () => {
    expect(shouldReconnectRealtimeChannel("SUBSCRIBED")).toBe(false);
    expect(shouldReconnectRealtimeChannel("CLOSED")).toBe(false);
  });
});

describe("realtimeReconnectDelayMs", () => {
  it("uses exponential backoff capped at max", () => {
    expect(realtimeReconnectDelayMs(1, 1000, 8000)).toBe(1000);
    expect(realtimeReconnectDelayMs(2, 1000, 8000)).toBe(2000);
    expect(realtimeReconnectDelayMs(3, 1000, 8000)).toBe(4000);
    expect(realtimeReconnectDelayMs(5, 1000, 8000)).toBe(8000);
  });
});

describe("RealtimeService reconnect", () => {
  const queryClient = {
    invalidateQueries: vi.fn(),
  };

  beforeEach(() => {
    vi.useFakeTimers();
    subscribeCallbacks.length = 0;
    channelInstances.length = 0;
    channelFactory.mockClear();
    removeChannel.mockClear();
    setAuth.mockClear();
    getSession.mockClear();
    resetRealtimeService();
  });

  afterEach(() => {
    vi.useRealTimers();
    resetRealtimeService();
  });

  async function flushSubscribe(expectedCount: number): Promise<void> {
    // startChannel awaits getSession/setAuth then creates the channel
    await vi.waitFor(() => {
      expect(subscribeCallbacks.length).toBeGreaterThanOrEqual(expectedCount);
    });
  }

  it("refreshes realtime auth before subscribing", async () => {
    const service = getRealtimeService(queryClient as never);

    service.subscribe({
      subscriptionId: "agent-abc",
      tables: ["agent_tools"],
    });

    await flushSubscribe(1);

    expect(getSession).toHaveBeenCalled();
    expect(setAuth).toHaveBeenCalledWith("fresh-token");
    expect(channelFactory).toHaveBeenCalledWith("realtime:agent-abc");
    expect(subscribeCallbacks.length).toBe(1);
  });

  it("subscribes only to safe invalidation rows and never forwards row content", async () => {
    const service = getRealtimeService(queryClient as never);
    const onUpdate = vi.fn();
    service.subscribe({ subscriptionId: "agent-a", tables: ["agent_tools", "voice_agents"], onUpdate });
    await flushSubscribe(1);
    const [type, options, receive] = channelInstances[0].on.mock.calls[0];
    expect(type).toBe("postgres_changes");
    expect(options).toEqual({event: "*", schema: "public", table: "agent_change_events", filter: "agent_id=eq.agent-a"});
    receive({ new: { agent_id: "agent-a", changed_at: "now", sensitive_config: "must-not-forward" } });
    expect(onUpdate).toHaveBeenCalledTimes(2);
    expect(JSON.stringify(onUpdate.mock.calls)).not.toContain("must-not-forward");
    expect(queryClient.invalidateQueries).toHaveBeenCalled();
    receive({ new: { agent_id: "agent-b" } });
    expect(onUpdate).toHaveBeenCalledTimes(2);
  });

  it("removes the dead channel and resubscribes after CHANNEL_ERROR", async () => {
    const service = getRealtimeService(queryClient as never);
    const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
    const errorSpy = vi.spyOn(console, "error").mockImplementation(() => {});

    service.subscribe({
      subscriptionId: "7ee02362-6ed2-4728-ba54-2a5ff56f92fe",
      tables: ["agent_tools", "voice_agents"],
    });
    await flushSubscribe(1);

    expect(subscribeCallbacks.length).toBe(1);
    const firstChannel = channelInstances[0];

    // Simulate idle JWT / WebSocket failure
    subscribeCallbacks[0]("CHANNEL_ERROR", new Error("Access token has expired"));

    // First reconnect attempt after base delay
    await vi.advanceTimersByTimeAsync(1000);
    await flushSubscribe(2);

    expect(removeChannel).toHaveBeenCalledWith(firstChannel);
    expect(channelFactory).toHaveBeenCalledTimes(2);
    expect(subscribeCallbacks.length).toBe(2);
    expect(warnSpy).toHaveBeenCalled();
    // Recoverable failures must not use console.error (Next.js error overlay)
    expect(
      errorSpy.mock.calls.some((call) =>
        String(call[0]).includes("Failed to subscribe to realtime"),
      ),
    ).toBe(false);
    expect(
      warnSpy.mock.calls.some((call) =>
        String(call[0]).includes("Failed to subscribe to realtime"),
      ),
    ).toBe(true);

    warnSpy.mockRestore();
    errorSpy.mockRestore();
  });

  it("does not return a dead channel when re-subscribing the same id", async () => {
    const service = getRealtimeService(queryClient as never);
    vi.spyOn(console, "warn").mockImplementation(() => {});

    service.subscribe({
      subscriptionId: "agent-1",
      tables: ["agent_tools"],
    });
    await flushSubscribe(1);

    subscribeCallbacks[0]("TIMED_OUT");
    await vi.advanceTimersByTimeAsync(1000);
    await flushSubscribe(2);

    // After reconnect, a fresh subscribe for same id should reuse the new channel
    // (not create a third) because the live channel is already in the map.
    const before = channelFactory.mock.calls.length;
    service.subscribe({
      subscriptionId: "agent-1",
      tables: ["agent_tools"],
    });
    expect(channelFactory.mock.calls.length).toBe(before);
  });
});
