import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { PlanPublishDialog } from "../plan-publish-dialog";

vi.mock("@/services/admin-plan-service", () => ({
  adminPlanService: {
    publishPlanVersion: vi.fn().mockResolvedValue({
      plan_version_id: "v1",
      publish_event_id: "e1",
      stripe_price_id: "price_1",
      migration_rows_created: 0,
      subscribers_migrated_immediately: 0,
    }),
  },
}));

const draftVersion = {
  id: "00000000-0000-0000-0000-000000000502",
  plan_product_id: "00000000-0000-0000-0000-000000000501",
  version_number: 2,
  status: "draft" as const,
  display_label: "Pro v2",
  billing_mode: "paid" as const,
  credit_grant_policy: "recurring" as const,
  price_amount_cents: 5900,
  currency: "USD",
  billing_interval: "monthly",
  trial_period_days: null,
  stripe_product_id: null,
  stripe_price_id: null,
  is_current_for_signup: false,
  published_at: null,
  legacy_subscription_plan_id: null,
  entitlements: [],
  created_at: "2026-08-07T00:00:00Z",
  updated_at: "2026-08-07T00:00:00Z",
};

describe("PlanPublishDialog", () => {
  it("renders migration policy controls when open", () => {
    render(
      <PlanPublishDialog
        version={draftVersion}
        open
        onOpenChange={() => undefined}
      />,
    );

    expect(screen.getByText("Publish plan version")).toBeInTheDocument();
    expect(screen.getByLabelText("Migration policy")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Publish" })).toBeInTheDocument();
  });

  it("calls publish service when Publish is clicked", async () => {
    const user = userEvent.setup();
    const { adminPlanService } = await import("@/services/admin-plan-service");

    render(
      <PlanPublishDialog
        version={draftVersion}
        open
        onOpenChange={() => undefined}
        onPublished={() => undefined}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Publish" }));

    expect(adminPlanService.publishPlanVersion).toHaveBeenCalledWith(
      draftVersion.id,
      expect.objectContaining({ migration_mode: "new_signups_only" }),
    );
  });
});
