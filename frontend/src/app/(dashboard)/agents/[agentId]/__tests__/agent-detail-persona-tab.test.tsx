import React from "react";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useAgentSystemPrompt } from "@/hooks/use-agent-queries";
import { voiceTemplateService } from "@/services/voice-template-service";
import type { AgentDetailFormState } from "../agent-detail-types";
import { AgentDetailPersonaTab } from "../agent-detail-persona-tab";

vi.mock("@/hooks/use-agent-queries", () => ({
  useAgentSystemPrompt: vi.fn(),
}));

vi.mock("@/services/voice-template-service", () => ({
  voiceTemplateService: {
    listTemplates: vi.fn(),
  },
}));

const AGENT_FORM: AgentDetailFormState = {
  name: "Front Desk Agent",
  persona: "Receptionist",
  tone: "Warm and concise",
  is_active: true,
  is_published_on_public_page: false,
  call_recording_enabled: true,
  use_platform_credits: true,
  instructions_markdown: "## Greeting\n\nKeep responses concise.",
  preset_id: null,
  is_demo: false,
  demo_slug: "",
  public_description: "",
  demo_public_result_url: "",
  demo_calls_remaining: 0,
  demo_max_call_duration_minutes: 15,
};

describe("AgentDetailPersonaTab", () => {
  beforeEach(() => {
    vi.mocked(useAgentSystemPrompt).mockReturnValue({
      data: "# System Prompt\n\n## Guardrails\n\nAlways be helpful.",
      isLoading: false,
    } as never);
    vi.mocked(voiceTemplateService.listTemplates).mockReturnValue(
      new Promise(() => undefined),
    );
  });

  it("renders additional instructions as Markdown and toggles into edit mode", () => {
    render(
      <AgentDetailPersonaTab
        agentId="agent-1"
        agentForm={AGENT_FORM}
        setAgentForm={vi.fn()}
        canEdit
      />,
    );

    expect(screen.getByText("Keep responses concise.")).toBeTruthy();
    expect(screen.queryByRole("textbox", { name: "Additional Instructions" })).toBeNull();

    fireEvent.click(screen.getByRole("button", { name: "Edit instructions" }));
    expect(screen.getByRole("textbox", { name: "Additional Instructions" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Preview instructions" })).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Preview instructions" }));
    expect(screen.getByText("Keep responses concise.")).toBeTruthy();
    expect(screen.queryByRole("textbox", { name: "Additional Instructions" })).toBeNull();
  });

  it("opens the compiled system prompt as rendered Markdown in a right drawer", async () => {
    render(
      <AgentDetailPersonaTab
        agentId="agent-1"
        agentForm={AGENT_FORM}
        setAgentForm={vi.fn()}
        canEdit
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /Preview System Prompt/i }));

    const drawer = await screen.findByRole("dialog");
    expect(within(drawer).getByRole("heading", { name: "System prompt preview" })).toBeTruthy();
    expect(within(drawer).getByRole("heading", { name: "Guardrails" })).toBeTruthy();
    expect(within(drawer).getByText("Always be helpful.")).toBeTruthy();
  });
});
