import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AgentCreatePhoneStage } from "../agent-create-phone-stage";

describe("AgentCreatePhoneStage", () => {
  it("explains that number assignment and purchase happen after creation", () => {
    render(
      <AgentCreatePhoneStage
        control={{} as never}
        onSkip={vi.fn()}
      />,
    );

    expect(
      screen.getByText(/buy a new number/i),
    ).toBeTruthy();
    expect(screen.getByText(/agent settings/i)).toBeTruthy();
    expect(screen.queryByText(/Twilio|webhook/i)).toBeNull();
  });
});
