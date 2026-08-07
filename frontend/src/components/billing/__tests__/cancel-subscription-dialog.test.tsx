/**
 * Cancel subscription dialog copy reflects cancel-at-period-end policy.
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { CancelSubscriptionDialog } from "@/components/billing/cancel-subscription-dialog";

describe("CancelSubscriptionDialog", () => {
  it("states full access continues until period end and no refund", () => {
    render(
      <CancelSubscriptionDialog
        open
        onOpenChange={() => {}}
        onCancel={async () => {}}
        accessUntil="2026-09-01T00:00:00.000Z"
      />,
    );

    expect(
      screen.getByText(/Full plan access continues until/i),
    ).toBeInTheDocument();
    expect(screen.getAllByText(/no refund is issued/i).length).toBeGreaterThan(0);
    expect(
      screen.queryByText(/All access to premium features will be removed/i),
    ).not.toBeInTheDocument();
  });
});
