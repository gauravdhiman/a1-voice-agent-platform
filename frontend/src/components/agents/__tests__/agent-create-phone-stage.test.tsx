import React from "react";
import { render, screen } from "@testing-library/react";
import { useForm } from "react-hook-form";
import { describe, expect, it, vi } from "vitest";
import {
  AgentCreatePhoneStage,
  type AgentCreatePhoneFormValues,
} from "@/components/agents/agent-create-phone-stage";

function PhoneStageHarness() {
  const { control } = useForm<AgentCreatePhoneFormValues>({
    defaultValues: { phone_number: "" },
  });

  return <AgentCreatePhoneStage control={control} onSkip={vi.fn()} />;
}

describe("AgentCreatePhoneStage", () => {
  it("explains the post-setup phone choices in business language", () => {
    render(<PhoneStageHarness />);

    expect(
      screen.getByText(
        /After you finish setting up the agent, you can choose one of your purchased numbers or buy a new number, or connect your own custom number for Lio/i,
      ),
    ).toBeInTheDocument();
    expect(screen.getByText(/after creation/i)).toBeInTheDocument();
    expect(
      screen.getByText(/start answering calls on that number/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        /Choose a purchased number, buy a new number, or connect your own custom number/i,
      ),
    ).toBeInTheDocument();
    expect(screen.getByText(/agent settings/i)).toBeInTheDocument();
    expect(screen.queryByText(/Twilio|webhook|API|mapping/i)).not.toBeInTheDocument();
  });
});
