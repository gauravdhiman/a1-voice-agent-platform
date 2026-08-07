import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { TelegramBotCredentialRow } from "@/components/notifications/telegram-bot-credential-row";

describe("TelegramBotCredentialRow", () => {
  it("shows configured badge and bot id when token is stored", () => {
    render(
      <TelegramBotCredentialRow
        configured
        botId="8895264981"
        value=""
        onChange={() => {}}
        onRemove={vi.fn()}
        editing={false}
        onStartEdit={() => {}}
        onCancelEdit={() => {}}
      />,
    );

    expect(screen.getByText("Configured")).toBeInTheDocument();
    expect(screen.getByText("Bot ID 8895264981")).toBeInTheDocument();
    expect(screen.getByLabelText("Telegram bot token stored")).toBeInTheDocument();
  });

  it("shows not configured state and add action", () => {
    render(
      <TelegramBotCredentialRow
        configured={false}
        value=""
        onChange={() => {}}
        onRemove={vi.fn()}
        editing={false}
        onStartEdit={() => {}}
        onCancelEdit={() => {}}
      />,
    );

    expect(screen.getByText("Not configured")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Add bot token/i })).toBeInTheDocument();
  });

  it("calls onStartEdit when update is clicked", async () => {
    const user = userEvent.setup();
    const onStartEdit = vi.fn();
    render(
      <TelegramBotCredentialRow
        configured
        botId="123456"
        value=""
        onChange={() => {}}
        onRemove={vi.fn()}
        editing={false}
        onStartEdit={onStartEdit}
        onCancelEdit={() => {}}
      />,
    );

    await user.click(screen.getByRole("button", { name: /Update token/i }));
    expect(onStartEdit).toHaveBeenCalledTimes(1);
  });
});
