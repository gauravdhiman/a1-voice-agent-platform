import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { agentService } from "@/services/agent-service";
import { phoneNumberService } from "@/services/phone-number-service";
import { PhoneNumberImportDialog } from "../phone-number-import-dialog";

vi.mock("@/services/agent-service", () => ({
  agentService: { getOrgAgents: vi.fn() },
}));

vi.mock("@/services/phone-number-service", () => ({
  phoneNumberService: { importNumber: vi.fn() },
}));

describe("PhoneNumberImportDialog", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(agentService.getOrgAgents).mockResolvedValue([]);
    vi.mocked(phoneNumberService.importNumber).mockResolvedValue({
      success: true,
      phone_number: { phone_number: "+14155550100" } as never,
      voice_url: "https://247ai.live/api/v1/voice/twilio/incoming?token=secret",
      status_callback:
        "https://247ai.live/api/v1/voice/twilio/status?token=secret",
      message: "Save both URLs in Twilio.",
    });
  });

  it("shows the Twilio help link with the generated webhook URLs", async () => {
    render(
      <PhoneNumberImportDialog
        organizationId="org-1"
        open
        onOpenChange={vi.fn()}
        onImportSuccess={vi.fn()}
      />,
    );

    fireEvent.change(screen.getByLabelText(/twilio phone number/i), {
      target: { value: "+14155550100" },
    });
    fireEvent.click(screen.getByRole("button", { name: /connect number/i }));

    expect(screen.getByRole("dialog").getAttribute("class")).toContain("p-6");
    const helpLink = await screen.findByRole("link", {
      name: /twilio webhook instructions/i,
    });
    expect(helpLink.getAttribute("href")).toBe(
      "https://www.twilio.com/docs/usage/webhooks",
    );
    await waitFor(() => {
      expect(phoneNumberService.importNumber).toHaveBeenCalledWith("org-1", {
        phone_number: "+14155550100",
        country_code: "US",
      });
    });
  });
});
