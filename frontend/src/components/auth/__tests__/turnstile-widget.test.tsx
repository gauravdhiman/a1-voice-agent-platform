import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { TurnstileWidget } from "@/components/auth/turnstile-widget";

const KEY = "NEXT_PUBLIC_TURNSTILE_SITE_KEY";

describe("TurnstileWidget", () => {
  const previousKey = process.env[KEY];

  beforeEach(() => {
    vi.clearAllMocks();
    delete process.env[KEY];
    delete window.turnstile;
  });

  afterEach(() => {
    if (previousKey === undefined) delete process.env[KEY];
    else process.env[KEY] = previousKey;
  });

  it("renders nothing without a site key (local dev)", () => {
    const { container } = render(<TurnstileWidget onVerify={vi.fn()} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders the widget container and verifies through Cloudflare", async () => {
    process.env[KEY] = "test-site-key";
    const onVerify = vi.fn();
    const renderMock = vi.fn().mockReturnValue("widget-1");
    window.turnstile = {
      render: renderMock,
      remove: vi.fn(),
    };

    render(<TurnstileWidget onVerify={onVerify} />);

    expect(
      await screen.findByTestId("turnstile-widget"),
    ).not.toBeNull();
    expect(renderMock).toHaveBeenCalledTimes(1);
    const [, options] = renderMock.mock.calls[0] as [
      unknown,
      { callback: (token: string) => void },
    ];
    options.callback("captcha-token-123");
    expect(onVerify).toHaveBeenCalledWith("captcha-token-123");
  });
});
