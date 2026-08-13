import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { phoneNumberService } from "@/services/phone-number-service";
import type { PhoneNumberWithAgent } from "@/types/phone-number";
import { AgentPhoneNumberSelector } from "../agent-phone-number-selector";

const { toast } = vi.hoisted(() => ({
  toast: { error: vi.fn(), success: vi.fn() },
}));

vi.mock("sonner", () => ({ toast }));

vi.mock("@/services/phone-number-service", () => ({
  phoneNumberService: {
    getOrganizationNumbers: vi.fn(),
    getAgentNumber: vi.fn(),
    getVerificationDetails: vi.fn(),
    assignToAgent: vi.fn(),
    unassignFromAgent: vi.fn(),
    importNumber: vi.fn(),
  },
}));

const AVAILABLE_NUMBER: PhoneNumberWithAgent = {
  id: "pn-1",
  phone_number: "+14155550100",
  phone_number_type: "local",
  country_code: "US",
  area_code: "415",
  provider: "twilio",
  provider_sid: "PN123",
  status: "purchased",
  assigned_agent_id: null,
  agent_name: null,
  monthly_cost_credits: 200,
  is_incoming_enabled: true,
  is_outgoing_enabled: false,
  billing_status: "active",
  billing_mode: "platform_rental",
  provisioning_source: "platform",
  management_mode: "platform_managed",
  configuration_status: "configured",
  configuration_error: null,
  last_verified_at: null,
  next_billing_at: null,
  billing_grace_ends_at: null,
  organization_id: "org-1",
  purchased_at: "2026-08-01T00:00:00Z",
  cancelled_at: null,
  created_at: "2026-08-01T00:00:00Z",
  updated_at: "2026-08-01T00:00:00Z",
};

describe("AgentPhoneNumberSelector", () => {
  beforeEach(() => {
    class ResizeObserverMock {
      observe() {}
      unobserve() {}
      disconnect() {}
    }
    globalThis.ResizeObserver = ResizeObserverMock as unknown as typeof ResizeObserver;
    Element.prototype.scrollIntoView = () => {};
    vi.clearAllMocks();
    vi.mocked(phoneNumberService.getOrganizationNumbers).mockResolvedValue({
      items: [AVAILABLE_NUMBER],
      total_count: 1,
      unused_count: 1,
    });
    vi.mocked(phoneNumberService.getAgentNumber).mockResolvedValue(null);
    vi.mocked(phoneNumberService.assignToAgent).mockResolvedValue({
      success: true,
      phone_number: { ...AVAILABLE_NUMBER, assigned_agent_id: "agent-1" },
    });
    vi.mocked(phoneNumberService.unassignFromAgent).mockResolvedValue({
      success: true,
      phone_number: { ...AVAILABLE_NUMBER, assigned_agent_id: null },
    });
    vi.mocked(phoneNumberService.importNumber).mockResolvedValue({
      success: true,
      phone_number: {
        ...AVAILABLE_NUMBER,
        id: "pn-custom",
        phone_number: "+14155550101",
        status: "verification_required",
        provisioning_source: "customer",
        management_mode: "customer_managed",
        billing_mode: "none",
        assigned_agent_id: "agent-1",
      },
      voice_url: "https://247ai.live/api/v1/twilio/voice?token=secret",
      status_callback:
        "https://247ai.live/api/v1/twilio/status?token=secret",
      message: "Save both URLs in Twilio.",
    });
    vi.mocked(phoneNumberService.getVerificationDetails).mockResolvedValue({
      phone_number_id: "pn-custom",
      phone_number: "+14155550101",
      voice_url: "https://247ai.live/api/v1/twilio/voice?token=secret",
      status_callback:
        "https://247ai.live/api/v1/twilio/status?token=secret",
      message: "Save both URLs in Twilio.",
    });
  });

  it("loads existing numbers and assigns the selected number to the agent", async () => {
    render(
      <AgentPhoneNumberSelector
        agentId="agent-1"
        organizationId="org-1"
        canEdit
      />,
    );

    await waitFor(() => {
      expect(phoneNumberService.getAgentNumber).toHaveBeenCalledWith(
        "org-1",
        "agent-1",
      );
    });
    fireEvent.click(screen.getByRole("combobox"));
    await waitFor(() => {
      expect(phoneNumberService.getOrganizationNumbers).toHaveBeenCalledWith("org-1");
    });
    expect(await screen.findByRole("option", { name: /415.*0100/ })).toBeTruthy();
    fireEvent.click(screen.getByRole("option", { name: /415.*0100/ }));

    await waitFor(() => {
      expect(phoneNumberService.assignToAgent).toHaveBeenCalledWith(
        "pn-1",
        { agent_id: "agent-1" },
        "org-1",
      );
    });
  });

  it("opens a right-side help drawer and shows webhook URLs after connecting a custom number", async () => {
    render(
      <AgentPhoneNumberSelector
        agentId="agent-1"
        organizationId="org-1"
        canEdit
      />,
    );

    await waitFor(() => {
      expect(phoneNumberService.getAgentNumber).toHaveBeenCalledWith(
        "org-1",
        "agent-1",
      );
    });
    fireEvent.click(screen.getByRole("combobox"));
    await waitFor(() => {
      expect(phoneNumberService.getOrganizationNumbers).toHaveBeenCalledWith("org-1");
    });
    await screen.findByRole("option", { name: /custom number/i });
    fireEvent.click(screen.getByRole("option", { name: /custom number/i }));

    expect(await screen.findByTestId("webhook-help-drawer")).toBeTruthy();
    expect(screen.getByTestId("webhook-help-drawer").getAttribute("class")).toContain(
      "p-6",
    );
    fireEvent.change(screen.getByLabelText(/twilio phone number/i), {
      target: { value: "+14155550101" },
    });
    fireEvent.click(screen.getByRole("button", { name: /connect number/i }));

    expect(
      await screen.findByText(/https:\/\/247ai\.live\/api\/v1\/twilio\/voice/),
    ).toBeTruthy();
    expect(phoneNumberService.importNumber).toHaveBeenCalledWith("org-1", {
      phone_number: "+14155550101",
      country_code: "US",
      agent_id: "agent-1",
    });
  });

  it("keeps verification details available after the setup drawer is closed", async () => {
    render(
      <AgentPhoneNumberSelector
        agentId="agent-1"
        organizationId="org-1"
        canEdit
      />,
    );

    await waitFor(() => {
      expect(phoneNumberService.getAgentNumber).toHaveBeenCalledWith(
        "org-1",
        "agent-1",
      );
    });
    fireEvent.click(screen.getByRole("combobox"));
    await waitFor(() => {
      expect(phoneNumberService.getOrganizationNumbers).toHaveBeenCalledWith("org-1");
    });
    fireEvent.click(await screen.findByRole("option", { name: /custom number/i }));
    fireEvent.change(screen.getByLabelText(/twilio phone number/i), {
      target: { value: "+14155550101" },
    });
    fireEvent.click(screen.getByRole("button", { name: /connect number/i }));

    await screen.findByText(/save these webhook settings/i);
    fireEvent.click(screen.getByRole("button", { name: /^done$/i }));

    const detailsButton = await screen.findByRole("button", {
      name: /view setup details/i,
    });
    fireEvent.click(detailsButton);

    await waitFor(() => {
      expect(phoneNumberService.getVerificationDetails).toHaveBeenCalledWith(
        "org-1",
        "pn-custom",
      );
    });
    expect((await screen.findAllByText(/token=secret/)).length).toBe(2);
  });

  it("clears the assignment without releasing the number", async () => {
    vi.mocked(phoneNumberService.getOrganizationNumbers).mockResolvedValue({
      items: [{ ...AVAILABLE_NUMBER, assigned_agent_id: "agent-1" }],
      total_count: 1,
      unused_count: 0,
    });
    vi.mocked(phoneNumberService.getAgentNumber).mockResolvedValue({
      ...AVAILABLE_NUMBER,
      assigned_agent_id: "agent-1",
    });

    render(
      <AgentPhoneNumberSelector
        agentId="agent-1"
        organizationId="org-1"
        canEdit
      />,
    );

    await waitFor(() => {
      expect(phoneNumberService.getAgentNumber).toHaveBeenCalledWith(
        "org-1",
        "agent-1",
      );
    });
    fireEvent.click(screen.getByRole("combobox"));
    await waitFor(() => {
      expect(phoneNumberService.getOrganizationNumbers).toHaveBeenCalledWith("org-1");
    });
    fireEvent.click(await screen.findByRole("option", { name: /no phone number/i }));

    await waitFor(() => {
      expect(phoneNumberService.unassignFromAgent).toHaveBeenCalledWith(
        "pn-1",
        "org-1",
      );
  });
  });

  it("surfaces a current-assignment load failure", async () => {
    vi.mocked(phoneNumberService.getAgentNumber).mockRejectedValueOnce(
      new Error("assignment unavailable"),
    );

    render(
      <AgentPhoneNumberSelector
        agentId="agent-1"
        organizationId="org-1"
        canEdit
      />,
    );

    expect(await screen.findByText("assignment unavailable")).toBeTruthy();
  });

  it("surfaces an organization inventory load failure when opened", async () => {
    vi.mocked(phoneNumberService.getOrganizationNumbers).mockRejectedValueOnce(
      new Error("inventory unavailable"),
    );

    render(
      <AgentPhoneNumberSelector
        agentId="agent-1"
        organizationId="org-1"
        canEdit
      />,
    );

    await waitFor(() => {
      expect(phoneNumberService.getAgentNumber).toHaveBeenCalled();
    });
    fireEvent.click(screen.getByRole("combobox"));
    expect(await screen.findByText("inventory unavailable")).toBeTruthy();
  });

  it("surfaces an assignment failure after selecting a number", async () => {
    vi.mocked(phoneNumberService.assignToAgent).mockRejectedValueOnce(
      new Error("assignment failed"),
    );

    render(
      <AgentPhoneNumberSelector
        agentId="agent-1"
        organizationId="org-1"
        canEdit
      />,
    );

    await waitFor(() => {
      expect(phoneNumberService.getAgentNumber).toHaveBeenCalled();
    });
    fireEvent.click(screen.getByRole("combobox"));
    await waitFor(() => {
      expect(phoneNumberService.getOrganizationNumbers).toHaveBeenCalled();
    });
    fireEvent.click(await screen.findByRole("option", { name: /415.*0100/ }));

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith("assignment failed");
    });
  });
});
