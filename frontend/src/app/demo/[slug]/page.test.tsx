import { act, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import userEvent from "@testing-library/user-event";

const {
  connectMock,
  disconnectMock,
  getCallTokenMock,
  getDemoAgentMock,
  replaceMock,
  useParamsMock,
  useRouterMock,
  useSearchParamsMock,
} = vi.hoisted(() => ({
  connectMock: vi.fn(),
  disconnectMock: vi.fn(),
  getCallTokenMock: vi.fn(),
  getDemoAgentMock: vi.fn(),
  replaceMock: vi.fn(),
  useParamsMock: vi.fn(() => ({ slug: "copper-ridge-service-request" })),
  useRouterMock: vi.fn(() => ({ replace: replaceMock })),
  useSearchParamsMock: vi.fn(() => new URLSearchParams()),
}));

vi.mock("next/navigation", () => ({
  useParams: useParamsMock,
  useRouter: useRouterMock,
  useSearchParams: useSearchParamsMock,
}));

vi.mock("@/services/demo-public-service", () => ({
  demoPublicService: {
    getCallToken: getCallTokenMock,
    getDemoAgent: getDemoAgentMock,
  },
}));

vi.mock("@/lib/pipecat-voice-client", () => ({
  connectPipecatVoiceCall: connectMock,
  disconnectPipecatVoiceCall: disconnectMock,
}));

vi.mock("@/components/agents-ui/agent-audio-radial-v4", () => ({
  AgentAudioRadialV4: () => <div data-testid="radial-visualizer" />,
}));

vi.mock("@/components/agents-ui/agent-audio-visualizer-livekit-bar-v4", () => ({
  AgentAudioVisualizerBarV4: () => <div data-testid="bar-visualizer" />,
}));

import DemoAgentPage from "./page";

describe("DemoAgentPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useParamsMock.mockReturnValue({ slug: "copper-ridge-service-request" });
    useRouterMock.mockReturnValue({ replace: replaceMock });
    useSearchParamsMock.mockReturnValue(new URLSearchParams());
    getDemoAgentMock.mockResolvedValue({
      id: "agent-1",
      name: "Jordan",
      demo_slug: "copper-ridge-service-request",
      persona: "Service coordinator",
      mission: "Capture service inquiries",
      tone: "Reassuring",
      public_description: "Capture a home-service request.",
      organization_id: "org-1",
      organization_name: "24x7 AI Demo Studio",
      demo_calls_remaining: -1,
      demo_max_call_duration_seconds: 900,
    });
    getCallTokenMock.mockResolvedValue({
      token: "voice-token",
      wsUrl: "ws://localhost:8480/ws",
      sessionId: "session-1",
      receiptToken: "receipt-token",
      demo_calls_remaining: -1,
      demo_max_call_duration_seconds: 900,
    });
    connectMock.mockImplementation(async (_token, _wsUrl, callbacks) => {
      callbacks.onConnected?.();
      return { disconnect: vi.fn() };
    });
    disconnectMock.mockResolvedValue(undefined);
  });

  it("routes a connected timeout/error to the private outcome receipt", async () => {
    const user = userEvent.setup();
    let callbacks: { onError?: (error: Error) => void } | undefined;
    connectMock.mockImplementationOnce(async (_token, _wsUrl, nextCallbacks) => {
      callbacks = nextCallbacks;
      nextCallbacks.onConnected?.();
      return { disconnect: vi.fn() };
    });

    render(<DemoAgentPage />);
    await screen.findByRole("button", { name: "Talk to Jordan" });
    await user.click(
      screen.getByRole("checkbox", {
        name: "I understand this is a public demo and will use dummy information.",
      }),
    );
    await user.click(screen.getByRole("button", { name: "Talk to Jordan" }));

    await waitFor(() => expect(connectMock).toHaveBeenCalled());
    await act(async () => {
      callbacks?.onError?.(new Error("Demo call duration limit reached"));
    });

    await waitFor(() => {
      expect(replaceMock).toHaveBeenCalledWith(
        "/demo/copper-ridge-service-request/outcome?token=receipt-token",
      );
    });
  });

  it("keeps a pre-connect failure visible for retry instead of opening a receipt", async () => {
    const user = userEvent.setup();
    connectMock.mockImplementationOnce(async (_token, _wsUrl, callbacks) => {
      callbacks.onError?.(new Error("Microphone permission was denied"));
      throw new Error("Microphone permission was denied");
    });

    render(<DemoAgentPage />);
    await screen.findByRole("button", { name: "Talk to Jordan" });
    await user.click(
      screen.getByRole("checkbox", {
        name: "I understand this is a public demo and will use dummy information.",
      }),
    );
    await user.click(screen.getByRole("button", { name: "Talk to Jordan" }));

    expect(
      await screen.findByText(
        "We couldn't connect to the voice assistant. Please try again later or contact the business if the problem continues.",
      ),
    ).toBeTruthy();
    expect(replaceMock).not.toHaveBeenCalled();
  });

  it("requires acknowledgement and links to Gmail alias guidance", async () => {
    const user = userEvent.setup();

    render(<DemoAgentPage />);
    const startButton = await screen.findByRole("button", {
      name: "Talk to Jordan",
    });

    expect(startButton).toBeDisabled();
    expect(
      screen.getByText(
        /This agent writes the information you share to a public demo data store that other visitors may see\./,
      ),
    ).toBeVisible();
    expect(
      screen.getByRole("link", { name: "Learn how Gmail aliases work" }),
    ).toHaveAttribute(
      "href",
      "https://support.google.com/mail/answer/22370?hl=en",
    );

    await user.click(
      screen.getByRole("checkbox", {
        name: "I understand this is a public demo and will use dummy information.",
      }),
    );

    expect(startButton).toBeEnabled();
  });
});
