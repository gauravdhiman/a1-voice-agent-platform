import React from "react";
import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { VoiceTemplate } from "@/types/voice-template";

vi.mock("@/services/voice-template-service", () => ({
  voiceTemplateService: {
    listTemplates: vi.fn(),
  },
}));

import { voiceTemplateService } from "@/services/voice-template-service";
import { TemplateSelectionStage } from "@/components/agents/agent-create-widget";

const template = {
  id: "tmpl-1",
  name: "Dental Receptionist",
  industry: "dental",
  description: "Friendly and professional dental office receptionist.",
  persona: "You are a friendly dental receptionist named [Agent Name].",
  tone: "warm, professional, reassuring",
  mission: "Help patients schedule appointments and answer common questions.",
  greeting: "Thank you for calling [Business Name]! This is [Agent Name].",
  custom_instructions: "Always confirm appointment details.",
  is_active: true,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
} satisfies VoiceTemplate;

describe("TemplateSelectionStage", () => {
  beforeEach(() => {
    vi.mocked(voiceTemplateService.listTemplates).mockResolvedValue([template]);
  });

  it("opens the full template preview in a right drawer", async () => {
    render(<TemplateSelectionStage onSelect={vi.fn()} onSkip={vi.fn()} />);

    await waitFor(() =>
      expect(screen.getByText("Dental Receptionist")).toBeInTheDocument(),
    );

    fireEvent.click(screen.getByRole("button", { name: "Preview" }));

    const drawer = await screen.findByRole("dialog");
    expect(
      within(drawer).getByText(
        "Friendly and professional dental office receptionist.",
      ),
    ).toBeInTheDocument();
    expect(within(drawer).getByText("dental")).toBeInTheDocument();
    expect(
      within(drawer).getByText(
        "Thank you for calling Your Business! This is your assistant.",
      ),
    ).toBeInTheDocument();
    expect(
      within(drawer).getByText(
        "Help patients schedule appointments and answer common questions.",
      ),
    ).toBeInTheDocument();
    expect(
      within(drawer).getByText("warm, professional, reassuring"),
    ).toBeInTheDocument();
    expect(
      within(drawer).getByText(
        "You are a friendly dental receptionist named your assistant.",
      ),
    ).toBeInTheDocument();
    expect(
      within(drawer).getByText("Always confirm appointment details."),
    ).toBeInTheDocument();
  });

  it("shows empty states for optional template details", async () => {
    vi.mocked(voiceTemplateService.listTemplates).mockResolvedValue([
      {
        ...template,
        description: null,
        persona: null,
        tone: null,
        mission: null,
        greeting: null,
        custom_instructions: null,
      },
    ]);

    render(<TemplateSelectionStage onSelect={vi.fn()} onSkip={vi.fn()} />);

    await waitFor(() =>
      expect(screen.getByText("Dental Receptionist")).toBeInTheDocument(),
    );
    fireEvent.click(screen.getByRole("button", { name: "Preview" }));

    const drawer = await screen.findByRole("dialog");
    expect(within(drawer).getAllByText("Not specified")).toHaveLength(5);
    expect(
      within(drawer).getByText(
        "Review the reusable instructions that will pre-fill this agent.",
      ),
    ).toBeInTheDocument();
  });
});
