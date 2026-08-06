import React from "react";
import { render, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({
  useSearchParams: vi.fn(),
}));

vi.mock("@/services/linkedin-auth-service", () => ({
  linkedinAuthService: {
    exchangeCode: vi.fn(),
  },
}));

import { useSearchParams } from "next/navigation";
import { linkedinAuthService } from "@/services/linkedin-auth-service";
import LinkedInCallbackPage from "./page";

describe("LinkedIn callback page", () => {
  const opener = {
    closed: false,
    postMessage: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useSearchParams).mockReturnValue(
      new URLSearchParams("code=linkedin-code&state=signed-state") as never,
    );
    vi.spyOn(window, "close").mockImplementation(() => undefined);
    Object.defineProperty(window, "opener", {
      configurable: true,
      value: opener,
    });
  });

  it("exchanges the callback code and posts the session to the opener", async () => {
    vi.mocked(linkedinAuthService.exchangeCode).mockResolvedValue({
      success: true,
      data: {
        accessToken: "access-token",
        refreshToken: "refresh-token",
        expiresIn: 3600,
      },
    });

    render(<LinkedInCallbackPage />);

    await waitFor(() => {
      expect(linkedinAuthService.exchangeCode).toHaveBeenCalledWith(
        "linkedin-code",
        "signed-state",
      );
    });
    expect(opener.postMessage).toHaveBeenCalledWith(
      {
        type: "linkedin-oauth-success",
        state: "signed-state",
        session: {
          accessToken: "access-token",
          refreshToken: "refresh-token",
          expiresIn: 3600,
        },
      },
      window.location.origin,
    );
    expect(window.close).toHaveBeenCalled();
  });

  it("posts a generic error when the backend exchange fails", async () => {
    vi.mocked(linkedinAuthService.exchangeCode).mockResolvedValue({
      success: false,
      error: "LinkedIn authentication could not be completed.",
    });

    render(<LinkedInCallbackPage />);

    await waitFor(() => {
      expect(opener.postMessage).toHaveBeenCalledWith(
        {
          type: "linkedin-oauth-error",
          state: "signed-state",
          message: "LinkedIn authentication could not be completed.",
        },
        window.location.origin,
      );
    });
    expect(window.close).toHaveBeenCalled();
  });
});
