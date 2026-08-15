import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AgentCreateToolsStage } from "@/components/agents/agent-create-tools-stage";

describe("AgentCreateToolsStage", () => {
  it("is informational and does not present tool selection controls", () => {
    render(<AgentCreateToolsStage />);

    expect(screen.getByRole("heading", { name: /Business tools/i })).toBeInTheDocument();
    expect(screen.getByText(/No tools to select right now/i)).toBeInTheDocument();
    expect(screen.getByText(/Other business services your team uses/i)).toBeInTheDocument();
    expect(screen.queryByText(/MCP|platform tools/i)).not.toBeInTheDocument();
    expect(screen.queryByRole("checkbox")).toBeNull();
    expect(screen.queryByRole("combobox")).toBeNull();
  });
});
