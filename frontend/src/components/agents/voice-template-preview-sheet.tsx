"use client";

import React from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { applyTemplatePlaceholders } from "@/lib/onboarding";
import type { VoiceTemplate } from "@/types/voice-template";

interface VoiceTemplatePreviewFieldProps {
  /** Human-readable name for the template field. */
  label: string;
  /** Field content, or null when the template does not define it. */
  value: string | null | undefined;
  /** Whether the content should preserve line breaks. */
  preserveWhitespace?: boolean;
}

/**
 * Displays one readable field in the voice-template preview drawer.
 *
 * @param props - Label, value, and formatting options for the field.
 * @returns A labelled preview block with an explicit empty-state message.
 */
function VoiceTemplatePreviewField({
  label,
  value,
  preserveWhitespace = false,
}: VoiceTemplatePreviewFieldProps) {
  const hasValue = Boolean(value?.trim());

  return (
    <div>
      <span className="text-sm font-medium text-foreground">{label}</span>
      <p
        className={`mt-1 rounded-lg bg-muted/50 p-3 text-sm ${
          preserveWhitespace ? "whitespace-pre-line" : ""
        } ${hasValue ? "text-muted-foreground" : "italic text-muted-foreground/70"}`}
      >
        {hasValue ? value : "Not specified"}
      </p>
    </div>
  );
}

export interface VoiceTemplatePreviewSheetProps {
  /** Template to preview; null closes the drawer content. */
  template: VoiceTemplate | null;
  /** Whether the right-side preview drawer is open. */
  open: boolean;
  /** Called when the drawer should open or close. */
  onOpenChange: (open: boolean) => void;
  /** Business name used to render the greeting placeholder. */
  businessName?: string;
  /** Agent name used to render greeting and persona placeholders. */
  agentName?: string;
  /** Optional callback for selecting the currently previewed template. */
  onSelect?: (template: VoiceTemplate) => void;
  /** Label for the optional template-selection action. */
  selectLabel?: string;
}

/**
 * Full voice-template preview presented in a right-side drawer.
 *
 * A voice template is a reusable starting configuration for an agent. The
 * drawer keeps the selection list compact while exposing every user-facing
 * template field before the user applies it.
 *
 * @param props - Template, drawer state, placeholder context, and actions.
 * @returns A right-side Sheet containing the complete template preview.
 */
export function VoiceTemplatePreviewSheet({
  template,
  open,
  onOpenChange,
  businessName = "",
  agentName = "",
  onSelect,
  selectLabel = "Use this template",
}: VoiceTemplatePreviewSheetProps) {
  const placeholderContext = { businessName, agentName };
  const industryLabel = template?.industry.replace(/_/g, " ");

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="flex w-full flex-col sm:max-w-lg"
        data-testid="voice-template-preview-sheet"
      >
        <SheetHeader className="border-b px-6 pb-4 pt-6">
          <div className="flex items-center gap-2 pr-8">
            <SheetTitle>{template?.name || "Template preview"}</SheetTitle>
            {industryLabel && (
              <Badge variant="secondary" className="capitalize">
                {industryLabel}
              </Badge>
            )}
          </div>
          <SheetDescription>
            {template?.description ||
              "Review the reusable instructions that will pre-fill this agent."}
          </SheetDescription>
        </SheetHeader>

        <div className="flex-1 space-y-5 overflow-y-auto px-6 py-5">
          <VoiceTemplatePreviewField
            label="Greeting"
            value={
              template?.greeting
                ? applyTemplatePlaceholders(
                    template.greeting,
                    placeholderContext,
                  )
                : null
            }
          />
          <VoiceTemplatePreviewField
            label="Mission"
            value={template?.mission}
          />
          <VoiceTemplatePreviewField label="Tone" value={template?.tone} />
          <VoiceTemplatePreviewField
            label="Persona"
            value={
              template?.persona
                ? applyTemplatePlaceholders(
                    template.persona,
                    placeholderContext,
                  )
                : null
            }
          />
          <VoiceTemplatePreviewField
            label="Custom instructions"
            value={template?.custom_instructions}
            preserveWhitespace
          />
        </div>

        <SheetFooter className="gap-2 border-t px-6 py-4">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Close
          </Button>
          {template && onSelect ? (
            <Button
              onClick={() => {
                onSelect(template);
                onOpenChange(false);
              }}
            >
              {selectLabel}
            </Button>
          ) : null}
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}
