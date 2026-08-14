"use client";

import type { Control, FieldValues } from "react-hook-form";
import { Button } from "@/components/ui/button";

export interface AgentCreatePhoneFormValues extends FieldValues {
  phone_number: string;
}

export interface AgentCreatePhoneStageProps<
  TFieldValues extends AgentCreatePhoneFormValues = AgentCreatePhoneFormValues,
> {
  control: Control<TFieldValues>;
  /** Skip phone setup and continue with an empty number */
  onSkip: () => void;
}

/**
 * Optional phone-number step for the agent creation wizard.
 *
 * Phone numbers are attached after the agent exists, so the assignment can
 * reference a concrete agent and use the phone_numbers source of truth.
 */
export function AgentCreatePhoneStage<
  TFieldValues extends AgentCreatePhoneFormValues = AgentCreatePhoneFormValues,
>({ onSkip }: AgentCreatePhoneStageProps<TFieldValues>) {
  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold mb-2">Phone number (optional)</h3>
        <p className="text-sm text-muted-foreground">
          After you finish setting up the agent, you can choose one of your
          purchased numbers or buy a new number, or connect your own custom
          number for Lio. Once connected, the agent can start answering calls
          on that number. These choices are available in the agent settings so
          you can keep the main setup quick and focused.
        </p>
      </div>

      <div className="bg-muted/30 rounded-lg p-4 border border-dashed space-y-3">
        <p className="text-sm text-muted-foreground">
          Choose a purchased number, buy a new number, or connect your own
          custom number from the agent&apos;s <strong>Phone number</strong> setting
          after creation.
        </p>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="text-muted-foreground hover:text-foreground px-0"
          onClick={onSkip}
          data-testid="agent-create-phone-skip"
        >
          Skip phone for now
        </Button>
      </div>
    </div>
  );
}
