import { act, fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  useTestCall: vi.fn(),
}));

vi.mock("@/hooks/use-test-call", () => ({
  useTestCall: mocks.useTestCall,
}));

vi.mock("@/components/agents-ui/agent-audio-radial-v4", () => ({
  AgentAudioRadialV4: ({ color, active }: { color?: string; active?: boolean }) => (
    <div data-testid="audio-visualizer" data-color={color} data-active={active} />
  ),
}));

import { TestCallModal } from "@/components/agents/test-call-modal";

function mockTestCall() {
  mocks.useTestCall.mockReturnValue({
    isConnecting: false,
    isConnected: false,
    startCall: vi.fn().mockResolvedValue(undefined),
    endCall: vi.fn(),
    toggleMute: vi.fn(),
    isMuted: false,
    isAgentSpeaking: false,
    isUserSpeaking: false,
    agentTrack: null,
    localTrack: null,
    levelManager: null,
  });
}

describe("TestCallModal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockTestCall();
  });

  it("lets a user close a failed test call without refreshing", () => {
    const onOpenChange = vi.fn();

    render(
      <TestCallModal
        open
        onOpenChange={onOpenChange}
        agentId="agent-1"
        agentName="Support Agent"
      />,
    );

    const hookOptions = mocks.useTestCall.mock.calls[0][0] as {
      onError?: (error: Error) => void;
    };
    act(() => {
      hookOptions.onError?.(new Error("Voice assistant unavailable"));
    });

    expect(screen.getByText("Voice assistant unavailable")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Close test call" }));

    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it("uses the shared radial visualizer for both call participants", () => {
    mocks.useTestCall.mockReturnValue({
      isConnecting: false,
      isConnected: true,
      startCall: vi.fn(),
      endCall: vi.fn(),
      toggleMute: vi.fn(),
      isMuted: false,
      isAgentSpeaking: true,
      isUserSpeaking: false,
      agentTrack: null,
      localTrack: {} as MediaStreamTrack,
      levelManager: { readLevels: vi.fn(() => ({ level: 0.4 })) },
    });

    render(
      <TestCallModal
        open
        onOpenChange={vi.fn()}
        agentId="agent-1"
        agentName="Support Agent"
      />,
    );

    expect(screen.getAllByTestId("audio-visualizer")).toHaveLength(2);
    const agentVisualizer = screen.getAllByTestId("audio-visualizer")[0];
    expect(agentVisualizer?.getAttribute("data-color")).toBe("#22d3ee");
    expect(agentVisualizer?.getAttribute("data-active")).toBe("true");
  });
});
