import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AgentCreateToolsStage } from "@/components/agents/agent-create-tools-stage";

describe("AgentCreateToolsStage", () => {
  it("is informational and does not present tool selection controls", () => {
    render(<AgentCreateToolsStage />);

    expect(screen.getByText(/Informational only/i)).toBeInTheDocument();
    expect(screen.getByText(/No tools to configure in this step/i)).toBeInTheDocument();
    expect(screen.queryByRole("checkbox")).toBeNull();
    expect(screen.queryByRole("combobox")).toBeNull();
  });
});
