import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const googleInitialize = vi.fn();
const googleRenderButton = vi.fn();
const googleCancel = vi.fn();
let triggerGoogleScriptError: (() => void) | undefined;

vi.mock("next/script", () => ({
  default: ({
    onLoad,
    onError,
  }: {
    onLoad?: () => void;
    onError?: () => void;
  }) => {
    triggerGoogleScriptError = onError;
    React.useEffect(() => {
      onLoad?.();
    }, [onLoad]);
    return null;
  },
}));

import { GoogleSignInButton } from "./google-sign-in-button";

describe("GoogleSignInButton", () => {
  beforeEach(() => {
    vi.stubEnv(
      "NEXT_PUBLIC_GOOGLE_CLIENT_ID",
      "test-client.apps.googleusercontent.com",
    );
    googleInitialize.mockReset();
    googleRenderButton.mockReset();
    googleCancel.mockReset();
    triggerGoogleScriptError = undefined;

    Object.defineProperty(window, "google", {
      configurable: true,
      value: {
        accounts: {
          id: {
            initialize: googleInitialize,
            renderButton: googleRenderButton,
            cancel: googleCancel,
          },
        },
      },
    });
  });

  afterEach(() => {
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("initializes Google's popup button with a hashed nonce", async () => {
    const onCredential = vi.fn();
    const onError = vi.fn();

    render(
      <GoogleSignInButton
        onCredential={onCredential}
        onError={onError}
        text="signin_with"
      />,
    );

    await waitFor(() => {
      expect(googleInitialize).toHaveBeenCalledTimes(1);
    });

    const [configuration] = googleInitialize.mock.calls[0];
    expect(configuration).toEqual(
      expect.objectContaining({
        client_id: "test-client.apps.googleusercontent.com",
        nonce: expect.any(String),
        ux_mode: "popup",
        use_fedcm_for_prompt: true,
      }),
    );
    expect(googleRenderButton).toHaveBeenCalledWith(
      expect.any(HTMLElement),
      expect.objectContaining({
        text: "signin_with",
      }),
    );

    await configuration.callback({ credential: "google-id-token" });

    await waitFor(() => {
      expect(onCredential).toHaveBeenCalledWith(
        "google-id-token",
        expect.any(String),
      );
    });
    expect(onCredential.mock.calls[0][1]).not.toBe(configuration.nonce);
    expect(onError).not.toHaveBeenCalled();
  });

  it("reports an invalid Google credential instead of calling Supabase", async () => {
    const onCredential = vi.fn();
    const onError = vi.fn();

    render(
      <GoogleSignInButton
        onCredential={onCredential}
        onError={onError}
        text="signup_with"
      />,
    );

    await waitFor(() => {
      expect(googleInitialize).toHaveBeenCalledTimes(1);
    });

    const [configuration] = googleInitialize.mock.calls[0];
    await configuration.callback({ credential: "" });

    expect(onCredential).not.toHaveBeenCalled();
    expect(onError).toHaveBeenCalledWith(
      "Google did not return an ID token. Please try again.",
    );
  });

  it("reports Web Crypto initialization failures", async () => {
    const onError = vi.fn();
    vi.spyOn(globalThis.crypto.subtle, "digest").mockRejectedValueOnce(
      new Error("Digest unavailable"),
    );

    render(
      <GoogleSignInButton
        onCredential={vi.fn()}
        onError={onError}
        text="signin_with"
      />,
    );

    await waitFor(() => {
      expect(onError).toHaveBeenCalledWith("Digest unavailable");
    });
  });

  it("reports when Web Crypto is unavailable", async () => {
    const onError = vi.fn();
    vi.stubGlobal("crypto", {
      getRandomValues: vi.fn(),
    });

    render(
      <GoogleSignInButton
        onCredential={vi.fn()}
        onError={onError}
        text="signin_with"
      />,
    );

    await waitFor(() => {
      expect(onError).toHaveBeenCalledWith(
        "Web Crypto is required for Google sign-in.",
      );
    });
  });

  it("does not render after unmounting during nonce generation", async () => {
    let resolveDigest: (value: ArrayBuffer) => void = () => undefined;
    const digestPromise = new Promise<ArrayBuffer>((resolve) => {
      resolveDigest = resolve;
    });
    vi.spyOn(globalThis.crypto.subtle, "digest").mockReturnValueOnce(
      digestPromise,
    );

    const { unmount } = render(
      <GoogleSignInButton
        onCredential={vi.fn()}
        onError={vi.fn()}
        text="signin_with"
      />,
    );

    await waitFor(() => {
      expect(globalThis.crypto.subtle.digest).toHaveBeenCalled();
    });

    unmount();
    resolveDigest(new ArrayBuffer(32));

    await waitFor(() => {
      expect(googleInitialize).not.toHaveBeenCalled();
      expect(googleRenderButton).not.toHaveBeenCalled();
    });
  });

  it("reports Google script loading failures", () => {
    const onError = vi.fn();

    render(
      <GoogleSignInButton
        onCredential={vi.fn()}
        onError={onError}
        text="signin_with"
      />,
    );

    triggerGoogleScriptError?.();

    expect(onError).toHaveBeenCalledWith(
      "Google sign-in could not load. Please check your connection and try again.",
    );
  });

  it("shows a configuration message when the public client ID is missing", () => {
    vi.stubEnv("NEXT_PUBLIC_GOOGLE_CLIENT_ID", "");

    render(
      <GoogleSignInButton
        onCredential={vi.fn()}
        onError={vi.fn()}
        text="signin_with"
      />,
    );

    expect(
      screen.getByRole("status", {
        name: /google sign-in is not configured/i,
      }),
    ).toBeTruthy();
    expect(googleInitialize).not.toHaveBeenCalled();
  });
});
