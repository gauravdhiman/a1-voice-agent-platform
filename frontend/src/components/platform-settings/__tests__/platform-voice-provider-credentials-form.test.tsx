import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  getCredentials: vi.fn(),
  saveCredential: vi.fn(),
  removeCredential: vi.fn(),
}));

vi.mock("@/services/platform-voice-credentials-service", () => ({
  platformVoiceCredentialsService: {
    getCredentials: mocks.getCredentials,
    saveCredential: mocks.saveCredential,
    removeCredential: mocks.removeCredential,
  },
}));

import { PlatformVoiceProviderCredentialsForm } from "../platform-voice-provider-credentials-form";

function renderForm() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <PlatformVoiceProviderCredentialsForm />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  mocks.getCredentials.mockResolvedValue({
    success: true,
    data: {
      providers: {
        google: {
          configured: false,
          environment_fallback_configured: true,
        },
        deepgram: {
          configured: false,
          environment_fallback_configured: false,
        },
        openai: {
          configured: false,
          environment_fallback_configured: false,
        },
        cartesia: {
          configured: false,
          environment_fallback_configured: false,
        },
        cerebras: {
          configured: false,
          environment_fallback_configured: false,
        },
        openrouter: {
          configured: false,
          environment_fallback_configured: false,
        },
        fish: {
          configured: false,
          environment_fallback_configured: false,
        },
      },
    },
  });
  mocks.saveCredential.mockResolvedValue({ success: true, data: { configured: true } });
  mocks.removeCredential.mockResolvedValue({ success: true });
});

afterEach(() => cleanup());

describe("PlatformVoiceProviderCredentialsForm", () => {
  it("shows environment fallback status and saves a write-only platform key", async () => {
    const user = userEvent.setup();
    renderForm();

    expect(await screen.findByText("Platform API Credentials")).toBeTruthy();
    expect(await screen.findByText("Environment fallback")).toBeTruthy();
    expect(
      await screen.findByText(/No platform API credential is stored. The matching environment value/),
    ).toBeTruthy();

    await user.click(screen.getAllByRole("button", { name: "Add API key" })[0]);
    expect(screen.queryByLabelText("Description")).toBeNull();
    await user.type(screen.getByLabelText("API key"), "platform-google-key");
    await user.click(screen.getByRole("button", { name: "Save API key" }));

    expect(mocks.saveCredential).toHaveBeenCalledWith(
      "google",
      "platform-google-key",
    );
    expect(await screen.findByText("Platform API Credentials")).toBeTruthy();
  });
});
