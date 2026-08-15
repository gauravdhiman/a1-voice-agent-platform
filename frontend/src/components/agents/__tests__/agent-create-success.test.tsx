import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AgentCreateSuccess } from "@/components/agents/agent-create-success";

describe("AgentCreateSuccess", () => {
  it("shows guidance links for skills and tools on the new agent", () => {
    render(
      <AgentCreateSuccess agentId="agent-123" agentName="Front Desk" />,
    );

    expect(screen.getByTestId("agent-create-success")).toBeInTheDocument();
    expect(screen.getByText(/Front Desk is ready/i)).toBeInTheDocument();
    expect(
      screen.getByText(/add knowledge and connect business tools/i),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /Connect business tools/i }),
    ).toBeInTheDocument();

    const skills = screen.getByTestId("agent-create-success-skills");
    const tools = screen.getByTestId("agent-create-success-tools");

    expect(skills).toHaveAttribute("href", "/agents/agent-123?tab=skills");
    expect(tools).toHaveAttribute("href", "/agents/agent-123?tab=tools");
  });
});
