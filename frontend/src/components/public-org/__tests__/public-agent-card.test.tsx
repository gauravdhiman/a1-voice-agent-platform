import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { PublicAgentCard } from "@/components/public-org/public-agent-card";
import type { PublicAgentSummary } from "@/types/public-org-page";

function makeAgent(
  overrides: Partial<PublicAgentSummary> = {},
): PublicAgentSummary {
  return {
    id: "agent-1",
    name: "Acme Concierge",
    persona: "Helpful concierge",
    mission: "Answer questions",
    is_demo: false,
    demo_calls_remaining: null,
    demo_max_call_duration_seconds: null,
    ...overrides,
  };
}

describe("PublicAgentCard demo availability", () => {
  it("shows available budget details on separate lines", () => {
    render(
      <PublicAgentCard
        slug="acme"
        agent={makeAgent({
          is_demo: true,
          demo_calls_remaining: 3,
          demo_max_call_duration_seconds: 600,
        })}
      />,
    );

    expect(screen.getByText("Demo agent")).toBeTruthy();
    const calls = screen.getByText("Calls: 3 trial calls remaining");
    const duration = screen.getByText("Duration: Maximum 10 minutes per call");
    expect(calls).toBeTruthy();
    expect(duration).toBeTruthy();
    expect(calls.tagName).toBe("DIV");
    expect(duration.tagName).toBe("DIV");
    expect(calls.parentElement).toBe(duration.parentElement);
    expect(
      screen
        .getByRole("link", { name: /talk to this agent/i })
        .getAttribute("href"),
    ).toBe("/o/acme/call/agent-1");
  });

  it("disables an exhausted demo without rendering a call link", () => {
    render(
      <PublicAgentCard
        slug="acme"
        agent={makeAgent({
          is_demo: true,
          demo_calls_remaining: 0,
          demo_max_call_duration_seconds: 600,
        })}
      />,
    );

    expect(
      (
        screen.getByRole("button", {
          name: "Demo unavailable",
        }) as HTMLButtonElement
      ).disabled,
    ).toBe(true);
    expect(screen.queryByText("Calls: No trial calls remaining")).toBeNull();
    expect(
      screen.queryByText("Duration: Maximum 10 minutes per call"),
    ).toBeNull();
    expect(
      screen.getByText(/contact the platform administrator/i),
    ).toBeTruthy();
    expect(
      screen.queryByRole("link", { name: /talk to this agent/i }),
    ).toBeNull();
  });

  it("keeps normal public agents unchanged", () => {
    render(<PublicAgentCard slug="acme" agent={makeAgent()} />);

    expect(screen.queryByText("Demo agent")).toBeNull();
    expect(
      screen.getByRole("link", { name: /talk to this agent/i }),
    ).toBeTruthy();
  });
});
