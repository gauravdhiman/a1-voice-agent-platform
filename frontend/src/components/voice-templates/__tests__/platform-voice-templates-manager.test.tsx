import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { toast } from "sonner";
import { PlatformVoiceTemplatesManager } from "@/components/voice-templates/platform-voice-templates-manager";
import { voiceTemplateService } from "@/services/voice-template-service";
import type { VoiceTemplate } from "@/types/voice-template";

vi.mock("@/services/voice-template-service", () => ({
  voiceTemplateService: {
    listAdminTemplates: vi.fn(),
    createTemplate: vi.fn(),
    updateTemplate: vi.fn(),
    deleteTemplate: vi.fn(),
  },
}));

vi.mock("@/components/markdown", () => ({
  MarkdownRenderer: ({ content }: { content: string }) => (
    <div data-testid="markdown-renderer">{content}</div>
  ),
}));

const TEMPLATE: VoiceTemplate = {
  id: "template-1",
  name: "Dental Receptionist",
  industry: "dental",
  description: "Friendly dental office receptionist.",
  persona: "You are a helpful dental receptionist.",
  tone: "warm, professional",
  mission: "Help patients schedule appointments.",
  greeting: "Thank you for calling {{org.name}}!",
  custom_instructions: "## Confirm details\n- Date\n- Time",
  is_active: true,
  created_at: "2026-08-14T00:00:00Z",
  updated_at: "2026-08-14T00:00:00Z",
};

const INACTIVE_TEMPLATE = { ...TEMPLATE, id: "template-2", name: "Archived Template", is_active: false };

describe("PlatformVoiceTemplatesManager", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(voiceTemplateService.listAdminTemplates).mockResolvedValue([
      TEMPLATE,
      INACTIVE_TEMPLATE,
    ]);
    vi.mocked(voiceTemplateService.createTemplate).mockResolvedValue(TEMPLATE);
    vi.mocked(voiceTemplateService.updateTemplate).mockResolvedValue(TEMPLATE);
    vi.mocked(voiceTemplateService.deleteTemplate).mockResolvedValue(undefined);
  });

  it("lists active and inactive templates and selects a template for inspection", async () => {
    render(<PlatformVoiceTemplatesManager />);

    expect((await screen.findAllByText("Dental Receptionist")).length).toBeGreaterThan(0);
    expect(screen.getByText("Archived Template")).toBeInTheDocument();

    expect(
      screen.queryByRole("button", { name: "Preview Dental Receptionist" }),
    ).not.toBeInTheDocument();
    await userEvent.click(screen.getAllByText("Dental Receptionist")[0]);
    expect(screen.getByRole("heading", { name: "Dental Receptionist" })).toBeInTheDocument();
    expect(screen.getByText(/# Mission/)).toBeInTheDocument();
    expect(screen.getByText(/# Instructions/)).toBeInTheDocument();
  });

  it("creates a template from the markdown-capable authoring form", async () => {
    const user = userEvent.setup();
    render(<PlatformVoiceTemplatesManager />);

    await user.click(await screen.findByRole("button", { name: /new template/i }));
    await user.type(screen.getByLabelText("Name"), "HVAC Dispatcher");
    await user.type(screen.getByLabelText("Industry"), "hvac");
    await user.type(screen.getByLabelText("Instructions"), "## Triage");
    await user.click(screen.getByRole("button", { name: /create template/i }));

    await waitFor(() =>
      expect(voiceTemplateService.createTemplate).toHaveBeenCalledWith(
        expect.objectContaining({
          name: "HVAC Dispatcher",
          industry: "hvac",
          custom_instructions: "## Triage",
        }),
      ),
    );
  });

  it("edits an existing template and removes it from agent pickers", async () => {
    const user = userEvent.setup();
    const updatedTemplate = {
      ...TEMPLATE,
      name: "Updated Dental Receptionist",
      industry: "healthcare",
      custom_instructions: "## Escalation",
      is_active: false,
    };
    vi.mocked(voiceTemplateService.updateTemplate).mockResolvedValue(updatedTemplate);

    render(<PlatformVoiceTemplatesManager />);

    await user.click((await screen.findAllByRole("button", { name: "Edit" }))[0]);
    await user.clear(screen.getByLabelText("Name"));
    await user.type(screen.getByLabelText("Name"), updatedTemplate.name);
    await user.clear(screen.getByLabelText("Industry"));
    await user.type(screen.getByLabelText("Industry"), updatedTemplate.industry);
    await user.clear(screen.getByLabelText("Instructions"));
    await user.type(
      screen.getByLabelText("Instructions"),
      updatedTemplate.custom_instructions,
    );
    await user.click(screen.getByRole("checkbox"));
    await user.click(screen.getByRole("button", { name: "Save changes" }));

    await waitFor(() =>
      expect(voiceTemplateService.updateTemplate).toHaveBeenCalledWith(
        TEMPLATE.id,
        expect.objectContaining({
          name: updatedTemplate.name,
          industry: updatedTemplate.industry,
          custom_instructions: updatedTemplate.custom_instructions,
          is_active: false,
        }),
      ),
    );
    expect((await screen.findAllByText("Updated Dental Receptionist")).length).toBe(2);
    expect(screen.getAllByText("Inactive").length).toBeGreaterThan(0);
  });

  it("filters the catalog and reports loading failures", async () => {
    const user = userEvent.setup();
    render(<PlatformVoiceTemplatesManager />);

    await user.type(screen.getByLabelText("Filter templates"), "archived");
    expect(await screen.findByText("Archived Template")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Preview Archived Template" }),
    ).not.toBeInTheDocument();

    vi.mocked(voiceTemplateService.listAdminTemplates).mockRejectedValueOnce(
      new Error("catalog unavailable"),
    );
    const { unmount } = render(<PlatformVoiceTemplatesManager />);
    await waitFor(() => expect(toast.error).toHaveBeenCalledWith("catalog unavailable"));
    unmount();
  });

  it("shows an empty state when the catalog has no templates", async () => {
    vi.mocked(voiceTemplateService.listAdminTemplates).mockResolvedValueOnce([]);

    render(<PlatformVoiceTemplatesManager />);

    expect(await screen.findByText("No templates found.")).toBeInTheDocument();
    expect(screen.getByText("Select a template to inspect its Markdown.")).toBeInTheDocument();
  });

  it("requires the exact Delete phrase before deleting", async () => {
    const user = userEvent.setup();
    render(<PlatformVoiceTemplatesManager />);

    await user.click(await screen.findByRole("button", { name: /delete dental receptionist/i }));
    const deleteButton = screen.getByRole("button", { name: "Delete Use Case Template" });
    expect(deleteButton).toBeDisabled();

    const confirmation = screen.getByLabelText(/type.*delete.*confirm/i);
    await user.type(confirmation, "delete");
    expect(deleteButton).toBeDisabled();
    await user.clear(confirmation);
    await user.type(confirmation, "Delete");
    expect(deleteButton).toBeEnabled();
    await user.click(deleteButton);

    await waitFor(() =>
      expect(voiceTemplateService.deleteTemplate).toHaveBeenCalledWith(TEMPLATE.id),
    );
  });

  it("previews Markdown in the editor and keeps the sheet open on save errors", async () => {
    const user = userEvent.setup();
    vi.mocked(voiceTemplateService.createTemplate).mockRejectedValueOnce(
      new Error("template could not be saved"),
    );
    render(<PlatformVoiceTemplatesManager />);

    await user.click(await screen.findByRole("button", { name: /new template/i }));
    expect(screen.getByText("How this template is used")).toBeInTheDocument();
    const usageNote = screen.getByRole("note", { name: "Template usage guidance" });
    expect(usageNote).toHaveClass("border-yellow-200", "bg-yellow-50");
    expect(
      screen.getByText(
        /Mission, greeting, and instructions become the generated Markdown\. Persona and tone populate the agent settings\. Business context comes from your organization details, not from this template\./,
      ),
    ).toBeInTheDocument();
    await user.type(screen.getByLabelText("Name"), "Plumbing Dispatcher");
    await user.type(screen.getByLabelText("Industry"), "plumbing");
    await user.type(screen.getByLabelText("Mission"), "Route urgent calls.");
    await user.type(screen.getByLabelText("Greeting"), "How can we help?");
    await user.type(screen.getByLabelText("Description"), "Dispatch support.");
    await user.type(screen.getByLabelText("Persona"), "You are a dispatcher.");
    await user.type(screen.getByLabelText("Tone"), "calm");
    await user.click(screen.getByRole("tab", { name: "Markdown preview" }));
    expect(screen.getByText("View Markdown source")).toBeInTheDocument();
    expect(
      screen
        .getAllByTestId("markdown-renderer")
        .some((node) => node.textContent?.includes("Route urgent calls.")),
    ).toBe(true);

    await user.click(screen.getByRole("button", { name: "Create template" }));
    await waitFor(() =>
      expect(toast.error).toHaveBeenCalledWith("template could not be saved"),
    );
    expect(screen.getByRole("button", { name: "Create template" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Cancel" }));
  });

  it("allows an admin to cancel a deletion without changing the catalog", async () => {
    const user = userEvent.setup();
    render(<PlatformVoiceTemplatesManager />);

    await user.click(await screen.findByRole("button", { name: /delete dental receptionist/i }));
    await user.click(screen.getByRole("button", { name: "Cancel" }));

    expect(voiceTemplateService.deleteTemplate).not.toHaveBeenCalled();
    expect(screen.getAllByText("Dental Receptionist").length).toBeGreaterThan(0);
  });
});
