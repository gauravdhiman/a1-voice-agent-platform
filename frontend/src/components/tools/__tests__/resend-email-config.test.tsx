import * as React from "react";

import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import {
  getResendEmailRoutesError,
  getResendEmailSenderError,
  isResendEmailConfigurationReady,
  parseResendRecipientInput,
  parseResendEmailRoutes,
  ResendEmailConfigEditor,
  ResendEmailRouteConfig,
} from "@/components/tools/resend-email-config";

const route: ResendEmailRouteConfig = {
  route_id: "customer_support",
  label: "Customer Support",
  recipients: ["support@example.com"],
};

describe("Resend email route configuration", () => {
  it("parses only the supported persisted route fields", () => {
    expect(
      parseResendEmailRoutes([
        {
          route_id: "support",
          label: "Support",
          recipients: ["support@example.com", 42],
          secret: "must be ignored",
        },
        "invalid",
      ]),
    ).toEqual([
      {
        route_id: "support",
        label: "Support",
        recipients: ["support@example.com"],
      },
    ]);
  });

  it("reports invalid route configuration before save", () => {
    expect(getResendEmailRoutesError([])).toBeNull();
    expect(
      getResendEmailRoutesError([
        { ...route, recipients: ["not-an-email"] },
      ]),
    ).toContain("invalid recipient");
    expect(getResendEmailSenderError("", "")).toContain("sender email");
    expect(getResendEmailSenderError("from@example.com", "Office\nDesk")).toContain(
      "single line",
    );
  });

  it("requires the org credential, sender, and a valid route before ready", () => {
    const config = {
      from_email: "noreply@example.com",
      from_name: "Example Business",
      routes: [route],
    };

    expect(isResendEmailConfigurationReady(config, false)).toBe(false);
    expect(
      isResendEmailConfigurationReady(
        { ...config, from_email: "" },
        true,
      ),
    ).toBe(false);
    expect(
      isResendEmailConfigurationReady({ ...config, routes: [] }, true),
    ).toBe(false);
    expect(isResendEmailConfigurationReady(config, true)).toBe(true);
  });

  it("adds and edits routes through the controlled callback", () => {
    const onChange = vi.fn();
    render(
      <ResendEmailConfigEditor
        routes={[route]}
        fromEmail="noreply@example.com"
        fromName="Example Business"
        onFromEmailChange={vi.fn()}
        onFromNameChange={vi.fn()}
        onChange={onChange}
        canEdit
      />,
    );

    fireEvent.change(screen.getByLabelText("Route ID"), {
      target: { value: "sales desk" },
    });
    expect(onChange).toHaveBeenLastCalledWith([
      { ...route, route_id: "sales_desk" },
    ]);

    fireEvent.click(screen.getByRole("button", { name: "Add email route" }));
    expect(onChange).toHaveBeenLastCalledWith([
      route,
      { route_id: "route_2", label: "New route", recipients: [] },
    ]);
  });

  it("keeps route ID focus while the editable key changes", async () => {
    const user = userEvent.setup();

    function ControlledEditor() {
      const [routes, setRoutes] = React.useState([route]);
      return (
        <ResendEmailConfigEditor
          routes={routes}
          fromEmail="noreply@example.com"
          fromName="Example Business"
          onFromEmailChange={vi.fn()}
          onFromNameChange={vi.fn()}
          onChange={setRoutes}
          canEdit
        />
      );
    }

    render(
      <ControlledEditor />,
    );

    const routeIdInput = screen.getByLabelText("Route ID");
    await user.click(routeIdInput);
    await user.clear(routeIdInput);
    await user.type(routeIdInput, "sales");

    expect(routeIdInput).toHaveFocus();
  });

  it("preserves comma-separated recipient text while parsing valid values", () => {
    const onChange = vi.fn();
    render(
      <ResendEmailConfigEditor
        routes={[route]}
        fromEmail="noreply@example.com"
        fromName="Example Business"
        onFromEmailChange={vi.fn()}
        onFromNameChange={vi.fn()}
        onChange={onChange}
        canEdit
      />,
    );

    const recipientsInput = screen.getByLabelText("Recipient email addresses");
    fireEvent.change(recipientsInput, {
      target: { value: "support@example.com," },
    });
    expect(recipientsInput).toHaveValue("support@example.com,");
    expect(onChange).toHaveBeenLastCalledWith([
      { ...route, recipients: ["support@example.com", ""] },
    ]);

    fireEvent.change(recipientsInput, {
      target: {
        value: "support@example.com, manager@example.com",
      },
    });
    expect(recipientsInput).toHaveValue(
      "support@example.com, manager@example.com",
    );
    expect(onChange).toHaveBeenLastCalledWith([
      {
        ...route,
        recipients: ["support@example.com", "manager@example.com"],
      },
    ]);
    expect(parseResendRecipientInput(" support@example.com , manager@example.com ")).toEqual([
      "support@example.com",
      "manager@example.com",
    ]);
  });

  it("prevents edits when the caller cannot edit the agent", () => {
    render(
      <ResendEmailConfigEditor
        routes={[route]}
        fromEmail="noreply@example.com"
        fromName="Example Business"
        onFromEmailChange={vi.fn()}
        onFromNameChange={vi.fn()}
        onChange={vi.fn()}
        canEdit={false}
      />,
    );

    expect(screen.getByLabelText("Route ID")).toBeDisabled();
    expect(screen.getByRole("button", { name: "Add email route" })).toBeDisabled();
  });
});
