"use client";

import type { Control, FieldPath, FieldValues } from "react-hook-form";
import { Button } from "@/components/ui/button";
import {
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";

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
 * Phone numbers can be added later from Phone Numbers / agent settings.
 */
export function AgentCreatePhoneStage<
  TFieldValues extends AgentCreatePhoneFormValues = AgentCreatePhoneFormValues,
>({ control, onSkip }: AgentCreatePhoneStageProps<TFieldValues>) {
  const phoneField = "phone_number" as FieldPath<TFieldValues>;

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold mb-2">Phone number (optional)</h3>
        <p className="text-sm text-muted-foreground">
          Attach an existing phone number now, or skip and configure one later.
          Numbers must be in E.164 format when provided.
        </p>
      </div>

      <FormField
        control={control}
        name={phoneField}
        render={({ field }) => (
          <FormItem>
            <FormLabel>Phone number</FormLabel>
            <FormControl>
              <Input
                {...field}
                placeholder="+14155551234"
                data-testid="agent-create-phone"
              />
            </FormControl>
            <FormDescription>
              Optional. Example: +14155551234. Leave blank to configure later.
            </FormDescription>
            <FormMessage />
          </FormItem>
        )}
      />

      <div className="bg-muted/30 rounded-lg p-4 border border-dashed space-y-3">
        <p className="text-sm text-muted-foreground">
          You can also purchase and assign numbers later from{" "}
          <strong>Phone Numbers</strong> in the dashboard.
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
