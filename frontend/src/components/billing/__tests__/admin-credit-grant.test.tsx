import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AdminCreditGrant } from "../admin-credit-grant";

const { grantAdminCredits, toast } = vi.hoisted(() => ({
  grantAdminCredits: vi.fn(),
  toast: { error: vi.fn(), success: vi.fn() },
}));

vi.mock("@/services/billing-service", () => ({
  billingService: { allocateAdminCredits: grantAdminCredits },
}));

vi.mock("sonner", () => ({ toast }));

describe("AdminCreditGrant", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    grantAdminCredits.mockResolvedValue({
      organization_id: "org-1",
      credits: 250,
      created: true,
      balance: {
        total_credits: 250,
        subscription_credits: 0,
        admin_granted_credits: 250,
        purchased_credits: 0,
        expiring_soon: 0,
        expires_at: null,
      },
      transaction: {},
    });
  });

  it("submits a platform credit grant with a reason", async () => {
    render(<AdminCreditGrant organizationId="org-1" onGranted={vi.fn()} />);

    fireEvent.click(
      screen.getByRole("button", { name: /allocate platform credits/i }),
    );
    fireEvent.change(screen.getByLabelText(/credit amount/i), {
      target: { value: "250" },
    });
    fireEvent.change(screen.getByLabelText(/reason/i), {
      target: { value: "Support compensation" },
    });
    fireEvent.click(screen.getByRole("button", { name: /^grant credits$/i }));

    await waitFor(() => {
      expect(grantAdminCredits).toHaveBeenCalledWith("org-1", {
        credits: 250,
        reason: "Support compensation",
        idempotency_key: expect.any(String),
      });
    });
    expect(toast.success).toHaveBeenCalled();
  });

  it("keeps the grant action disabled until the required fields are valid", () => {
    render(<AdminCreditGrant organizationId="org-1" />);

    fireEvent.click(
      screen.getByRole("button", { name: /allocate platform credits/i }),
    );

    expect(
      screen.getByRole("button", { name: /^grant credits$/i }),
    ).toBeDisabled();
  });

  it("reuses the same idempotency key when a submission is retried", async () => {
    grantAdminCredits
      .mockRejectedValueOnce(new Error("Temporary failure"))
      .mockResolvedValueOnce({
        organization_id: "org-1",
        credits: 250,
        created: true,
        balance: {},
        transaction: {},
      });
    render(<AdminCreditGrant organizationId="org-1" />);

    fireEvent.click(
      screen.getByRole("button", { name: /allocate platform credits/i }),
    );
    fireEvent.change(screen.getByLabelText(/credit amount/i), {
      target: { value: "250" },
    });
    fireEvent.change(screen.getByLabelText(/reason/i), {
      target: { value: "Support compensation" },
    });
    const submit = screen.getByRole("button", { name: /^grant credits$/i });

    fireEvent.click(submit);
    await waitFor(() => expect(toast.error).toHaveBeenCalled());
    fireEvent.click(submit);

    await waitFor(() => expect(grantAdminCredits).toHaveBeenCalledTimes(2));
    expect(grantAdminCredits.mock.calls[0][1].idempotency_key).toBe(
      grantAdminCredits.mock.calls[1][1].idempotency_key,
    );
  });
});
