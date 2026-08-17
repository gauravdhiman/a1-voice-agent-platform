import { beforeEach, describe, expect, it, vi } from "vitest";
import { apiClient } from "@/lib/api/client";
import { voiceTemplateService } from "@/services/voice-template-service";

vi.mock("@/lib/api/client", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

const TEMPLATE = {
  id: "template-1",
  name: "Dental Receptionist",
  industry: "dental",
  description: null,
  persona: null,
  tone: null,
  mission: null,
  greeting: null,
  custom_instructions: "# Instructions",
  is_active: true,
  created_at: "2026-08-14T00:00:00Z",
  updated_at: "2026-08-14T00:00:00Z",
};

describe("voiceTemplateService admin CRUD", () => {
  beforeEach(() => vi.clearAllMocks());

  it("keeps the public picker methods active-only and industry-filterable", async () => {
    vi.mocked(apiClient.get)
      .mockResolvedValueOnce({ data: [TEMPLATE], success: true })
      .mockResolvedValueOnce({ data: TEMPLATE, success: true });

    await expect(voiceTemplateService.listTemplates("home services")).resolves.toEqual([
      TEMPLATE,
    ]);
    await expect(voiceTemplateService.getTemplate(TEMPLATE.id)).resolves.toEqual(
      TEMPLATE,
    );

    expect(apiClient.get).toHaveBeenNthCalledWith(
      1,
      "/api/v1/voice-templates?industry=home%20services",
    );
    expect(apiClient.get).toHaveBeenNthCalledWith(
      2,
      `/api/v1/voice-templates/${TEMPLATE.id}`,
    );
  });

  it("loads the management catalog including inactive templates", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: [TEMPLATE], success: true });

    await expect(voiceTemplateService.listAdminTemplates()).resolves.toEqual([
      TEMPLATE,
    ]);
    expect(apiClient.get).toHaveBeenCalledWith(
      "/api/v1/platform/voice-templates/",
    );
  });

  it("creates, updates, and deletes a template through admin endpoints", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: TEMPLATE, success: true });
    vi.mocked(apiClient.put).mockResolvedValue({ data: TEMPLATE, success: true });
    vi.mocked(apiClient.delete).mockResolvedValue({ data: null, success: true });

    const payload = { name: TEMPLATE.name, industry: TEMPLATE.industry };
    await expect(voiceTemplateService.createTemplate(payload)).resolves.toEqual(
      TEMPLATE,
    );
    await expect(
      voiceTemplateService.updateTemplate(TEMPLATE.id, { description: "Updated" }),
    ).resolves.toEqual(TEMPLATE);
    await expect(
      voiceTemplateService.deleteTemplate(TEMPLATE.id),
    ).resolves.toBeUndefined();

    expect(apiClient.post).toHaveBeenCalledWith(
      "/api/v1/platform/voice-templates/",
      payload,
    );
    expect(apiClient.put).toHaveBeenCalledWith(
      `/api/v1/platform/voice-templates/${TEMPLATE.id}`,
      { description: "Updated" },
    );
    expect(apiClient.delete).toHaveBeenCalledWith(
      `/api/v1/platform/voice-templates/${TEMPLATE.id}`,
    );
  });
});
