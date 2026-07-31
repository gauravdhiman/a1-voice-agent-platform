import React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ProviderCredentialRow } from "../provider-credential-row";

describe("ProviderCredentialRow", () => {
  it("shows Add API key when not configured", () => {
    render(
      <ProviderCredentialRow
        label="Deepgram API key"
        configured={false}
        value=""
        editing={false}
        onChange={vi.fn()}
        onRemove={vi.fn()}
        onStartEdit={vi.fn()}
        onCancelEdit={vi.fn()}
      />,
    );

    expect(screen.getByText("Not configured")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /add api key/i }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /remove key/i }),
    ).not.toBeInTheDocument();
  });

  it("shows Update and Remove when configured", () => {
    render(
      <ProviderCredentialRow
        label="OpenAI API key"
        configured={true}
        value=""
        editing={false}
        onChange={vi.fn()}
        onRemove={vi.fn()}
        onStartEdit={vi.fn()}
        onCancelEdit={vi.fn()}
      />,
    );

    expect(screen.getByText("Configured")).toBeInTheDocument();
    expect(screen.getByText("••••••••••••")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /update key/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /remove key/i }),
    ).toBeInTheDocument();
  });

  it("calls onRemove after confirming the dialog", async () => {
    const user = userEvent.setup();
    const onRemove = vi.fn().mockResolvedValue(undefined);

    render(
      <ProviderCredentialRow
        label="Cartesia API key"
        configured={true}
        value=""
        editing={false}
        onChange={vi.fn()}
        onRemove={onRemove}
        onStartEdit={vi.fn()}
        onCancelEdit={vi.fn()}
      />,
    );

    await user.click(screen.getByRole("button", { name: /remove key/i }));
    expect(
      screen.getByRole("heading", { name: /remove cartesia api key/i }),
    ).toBeInTheDocument();

    await user.click(
      screen.getByRole("button", { name: /^remove key$/i }),
    );

    expect(onRemove).toHaveBeenCalledTimes(1);
  });

  it("shows the password field while editing", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();

    render(
      <ProviderCredentialRow
        label="Google API key"
        configured={false}
        value=""
        editing={true}
        onChange={onChange}
        onRemove={vi.fn()}
        onStartEdit={vi.fn()}
        onCancelEdit={vi.fn()}
      />,
    );

    const input = screen.getByPlaceholderText(/paste your api key/i);
    await user.type(input, "secret");
    expect(onChange).toHaveBeenCalled();
  });
});
