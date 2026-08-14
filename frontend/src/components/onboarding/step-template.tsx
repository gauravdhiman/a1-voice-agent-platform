"use client";

import React, { useEffect, useState } from "react";
import {
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Eye,
  Loader2,
} from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { VoiceTemplatePreviewSheet } from "@/components/agents/voice-template-preview-sheet";
import {
  canContinueTemplateStep,
  canSkipTemplateStep,
  type OnboardingWizardState,
} from "@/lib/onboarding";
import { cn } from "@/lib/utils";
import { voiceTemplateService } from "@/services/voice-template-service";
import type { VoiceTemplate } from "@/types/voice-template";

export interface StepTemplateProps {
  state: OnboardingWizardState;
  onChange: (update: Partial<OnboardingWizardState>) => void;
  onNext: () => void;
  onSkip: () => void;
  onBack: () => void;
}

/**
 * Step 2 — agent name plus optional voice template selection.
 *
 * Continue requires an agent name and a selected template. Skip only requires
 * an agent name so founders can leave without a template.
 */
export function StepTemplate({
  state,
  onChange,
  onNext,
  onSkip,
  onBack,
}: StepTemplateProps) {
  const [templates, setTemplates] = useState<VoiceTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [previewTemplate, setPreviewTemplate] = useState<VoiceTemplate | null>(
    null,
  );

  useEffect(() => {
    voiceTemplateService
      .listTemplates()
      .then(setTemplates)
      .catch(() => toast.error("Failed to load templates"))
      .finally(() => setLoading(false));
  }, []);

  const industryMatch = templates.filter((t) => t.industry === state.industry);
  const otherTemplates = templates.filter((t) => t.industry !== state.industry);
  const sorted = [...industryMatch, ...otherTemplates];
  const canContinue = canContinueTemplateStep(state);
  const canSkip = canSkipTemplateStep(state);

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">
          Name your agent &amp; pick a template
        </h2>
        <p className="text-gray-500 mt-1">
          Choose how callers hear your agent. Templates are optional — you can
          skip and configure later.
        </p>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Agent name <span className="text-red-500">*</span>
        </label>
        <Input
          placeholder="e.g. Riley, Front Desk, Alex"
          value={state.agentName}
          onChange={(e) => onChange({ agentName: e.target.value })}
          data-testid="onboarding-agent-name"
        />
        <p className="text-xs text-gray-400 mt-1">
          This name is used in greetings instead of the template&apos;s default
          name.
        </p>
      </div>

      {loading ? (
        <div className="flex justify-center py-10">
          <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
        </div>
      ) : (
        <div className="space-y-3 max-h-72 overflow-y-auto pr-1">
          {sorted.map((template) => {
            const isSelected = state.selectedTemplate?.id === template.id;
            const isMatch = template.industry === state.industry;
            return (
              <div
                key={template.id}
                onClick={() => onChange({ selectedTemplate: template })}
                className={cn(
                  "p-4 border-2 rounded-lg cursor-pointer transition-all",
                  isSelected
                    ? "border-blue-500 bg-blue-50"
                    : "border-gray-200 hover:border-blue-200 hover:bg-gray-50",
                )}
                data-testid={`onboarding-template-${template.id}`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-gray-900">
                        {template.name}
                      </span>
                      {isMatch && (
                        <Badge
                          variant="secondary"
                          className="text-xs bg-blue-100 text-blue-700"
                        >
                          Recommended
                        </Badge>
                      )}
                      {isSelected && (
                        <CheckCircle2 className="w-5 h-5 text-blue-500 ml-auto" />
                      )}
                    </div>
                    <p className="text-sm text-gray-500 mt-0.5">
                      {template.description}
                    </p>
                    {template.tone && (
                      <p className="text-xs text-gray-400 mt-1">
                        Tone: {template.tone}
                      </p>
                    )}
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="ml-2 shrink-0"
                    onClick={(e) => {
                      e.stopPropagation();
                      setPreviewTemplate(template);
                    }}
                  >
                    <Eye className="w-4 h-4 mr-1" /> Preview
                  </Button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      <VoiceTemplatePreviewSheet
        template={previewTemplate}
        open={!!previewTemplate}
        onOpenChange={(open) => !open && setPreviewTemplate(null)}
        businessName={state.businessName}
        agentName={state.agentName}
        onSelect={(template) => onChange({ selectedTemplate: template })}
        selectLabel="Select this template"
      />

      <div className="flex gap-3">
        <Button variant="outline" onClick={onBack} className="w-32">
          <ChevronLeft className="w-4 h-4 mr-1" /> Back
        </Button>
        <Button
          onClick={onNext}
          disabled={!canContinue}
          className="flex-1"
          size="lg"
          data-testid="onboarding-template-continue"
        >
          Continue <ChevronRight className="w-4 h-4 ml-2" />
        </Button>
      </div>

      <div className="text-center">
        <Button
          variant="ghost"
          size="sm"
          onClick={onSkip}
          disabled={!canSkip}
          className="text-muted-foreground hover:text-foreground"
          data-testid="onboarding-template-skip"
        >
          Skip template and continue
        </Button>
      </div>
    </div>
  );
}
