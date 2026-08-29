import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  connect: vi.fn(),
  disconnect: vi.fn(),
  getTestToken: vi.fn(),
}));

vi.mock("@/lib/pipecat-voice-client", () => ({
  connectPipecatVoiceCall: mocks.connect,
  disconnectPipecatVoiceCall: mocks.disconnect,
}));

vi.mock("@/services/agent-service", () => ({
  agentService: { getTestToken: mocks.getTestToken },
}));

import { useTestCall } from "@/hooks/use-test-call";

describe("useTestCall", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.getTestToken.mockResolvedValue({
      token: "session-token",
      wsUrl: "ws://voice/ws",
    });
    mocks.disconnect.mockResolvedValue(undefined);
  });

  it("does not send a second disconnect when the voice server closes the socket", async () => {
    let callbacks: { onConnected?: () => void; onDisconnected?: () => void } =
      {};
    mocks.connect.mockImplementation(async (_token, _wsUrl, nextCallbacks) => {
      callbacks = nextCallbacks;
      nextCallbacks.onClientCreated?.({ enableMic: vi.fn() });
      nextCallbacks.onConnected?.();
      return { enableMic: vi.fn() };
    });
    const onDisconnected = vi.fn();
    const { result } = renderHook(() =>
      useTestCall({ agentId: "agent-1", onDisconnected }),
    );

    await act(async () => {
      await result.current.startCall();
    });
    expect(result.current.isConnected).toBe(true);

    await act(async () => {
      callbacks.onDisconnected?.();
    });

    expect(mocks.disconnect).not.toHaveBeenCalled();
    expect(onDisconnected).toHaveBeenCalledTimes(1);
    expect(result.current.isConnected).toBe(false);

    act(() => result.current.endCall());
    expect(mocks.disconnect).not.toHaveBeenCalled();
    expect(onDisconnected).toHaveBeenCalledTimes(1);
  });

  it("closes a client when hangup races the connection promise", async () => {
    let resolveConnection!: (client: { enableMic: ReturnType<typeof vi.fn> }) =>
      void;
    let connectionStarted!: () => void;
    const started = new Promise<void>((resolve) => {
      connectionStarted = resolve;
    });
    const client = { enableMic: vi.fn() };

    mocks.connect.mockImplementation(async (_token, _wsUrl, nextCallbacks) => {
      nextCallbacks.onClientCreated?.(client);
      nextCallbacks.onConnected?.();
      connectionStarted();
      await new Promise<void>((resolve) => {
        resolveConnection = () => resolve();
      });
      return client;
    });

    const { result } = renderHook(() => useTestCall({ agentId: "agent-1" }));
    let startPromise!: Promise<void>;
    act(() => {
      startPromise = result.current.startCall();
    });
    await act(async () => {
      await started;
    });

    act(() => result.current.endCall());
    resolveConnection(client);
    await act(async () => {
      await startPromise;
    });

    expect(mocks.disconnect).toHaveBeenCalledWith(client);
    expect(result.current.isConnected).toBe(false);
    expect(result.current.isConnecting).toBe(false);
  });
});
