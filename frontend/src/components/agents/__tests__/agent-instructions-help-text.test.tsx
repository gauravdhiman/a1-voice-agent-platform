import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AgentInstructionsHelpText } from "@/components/agents/agent-instructions-help-text";

describe("AgentInstructionsHelpText", () => {
  it("explains Markdown guidance and supported dynamic context", () => {
    render(<AgentInstructionsHelpText />);

    expect(
      screen.getByRole("link", { name: "markdown format" }).getAttribute("href"),
    ).toBe("https://www.markdownguide.org/basic-syntax/");
    expect(screen.getByText("{{org.name}}")).toBeTruthy();
    expect(screen.getByText("{{org.industry}}")).toBeTruthy();
    expect(screen.getByText("{{agent.name}}")).toBeTruthy();
  });
});
