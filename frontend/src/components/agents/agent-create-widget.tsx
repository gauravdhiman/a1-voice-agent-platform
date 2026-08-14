"use client";

import React, { useState, useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { useSearchParams } from "next/navigation";
import { useOrganization } from "@/contexts/organization-context";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Bot, Phone, ChevronRight, ChevronLeft, Check, Info, Mic, Eye, Loader2, CheckCircle2, SkipForward, Plug } from "lucide-react";
import { useCreateAgent } from "@/hooks/use-agent-queries";
import { usePresetCatalog } from "@/hooks/use-preset-queries";
import { DEFAULT_PRESET_DISPLAY } from "@/types/preset";
import { voiceTemplateService } from "@/services/voice-template-service";
import { toast } from "sonner";
import type { VoiceAgentCreate } from "@/types/agent";
import type { VoiceTemplate } from "@/types/voice-template";
import { AgentCreatePhoneStage } from "@/components/agents/agent-create-phone-stage";
import { AgentCreateSuccess } from "@/components/agents/agent-create-success";
import { AgentCreateToolsStage } from "@/components/agents/agent-create-tools-stage";
import { PresetPicker } from "@/components/agents/preset-picker";
import {
  isOptionalE164Phone,
  normalizeOptionalPhone,
  resolveAgentCreatePromptFields,
} from "@/lib/agent-create";
import { cn } from "@/lib/utils";

const formSchema = z.object({
  organization_id: z.string().min(1, "Organization is required"),
  name: z.string().min(1, "Agent name is required"),
  phone_number: z
    .string()
    .refine(
      (value) => isOptionalE164Phone(value),
      "Phone number must be in E.164 format with at least 8 digits (e.g., +14155551234), or left blank",
    ),
  persona: z.string().min(1, "Persona is required"),
  tone: z.string().min(1, "Tone is required"),
  mission: z.string().min(1, "Mission is required"),
  custom_instructions: z.string().optional(),
  is_active: z.boolean(),
  // Voice-engine preset (Phase 4). null = system default. Optional
  // UUID when a published preset is chosen. Never an empty string — the backend
  // UUID validator would 400, so the picker emits `null` for the default.
  preset_id: z.string().uuid().optional().nullable(),
});

type FormData = z.infer<typeof formSchema>;

type Stage = "template" | "basic" | "phone" | "tools" | "review" | "success";

const stageConfig = {
  template: { step: 1, title: "Template", icon: Mic },
  basic: { step: 2, title: "Basic Information", icon: Bot },
  phone: { step: 3, title: "Phone Number", icon: Phone },
  tools: { step: 4, title: "Business Tools", icon: Plug },
  review: { step: 5, title: "Review & Create", icon: Check },
  success: { step: 6, title: "Done", icon: CheckCircle2 },
};

function StepIndicator({
  stages,
  currentStage,
}: {
  stages: Stage[];
  currentStage: Stage;
}) {
  const currentIndex = stages.indexOf(currentStage);

  return (
    <div className="flex items-center justify-between mb-8">
      {stages.map((stage, index) => {
        const config = stageConfig[stage];
        const isCompleted = index < currentIndex;
        const isCurrent = index === currentIndex;

        return (
          <React.Fragment key={stage}>
            <div className="flex flex-col items-center flex-1">
              <div
                className={cn(
                  "w-10 h-10 rounded-full flex items-center justify-center text-sm font-medium transition-all",
                  isCompleted
                    ? "bg-primary text-primary-foreground"
                    : isCurrent
                      ? "bg-primary text-primary-foreground ring-4 ring-primary/20"
                      : "bg-muted text-muted-foreground",
                )}
              >
                {isCompleted ? (
                  <Check className="h-5 w-5" />
                ) : (
                  <config.icon className="h-5 w-5" />
                )}
              </div>
              <span
                className={cn(
                  "text-xs mt-2 font-medium",
                  isCurrent
                    ? "text-foreground"
                    : isCompleted
                      ? "text-primary"
                      : "text-muted-foreground",
                )}
              >
                {config.title}
              </span>
            </div>
            {index < stages.length - 1 && (
              <div
                className={cn(
                  "flex-1 h-0.5 mx-4 transition-colors",
                  isCompleted ? "bg-primary" : "bg-muted",
                )}
              />
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
}

function TemplateSelectionStage({
  onSelect,
  onSkip,
}: {
  onSelect: (template: VoiceTemplate) => void;
  onSkip: () => void;
}) {
  const [templates, setTemplates] = useState<VoiceTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<VoiceTemplate | null>(null);
  const [preview, setPreview] = useState<VoiceTemplate | null>(null);

  useEffect(() => {
    voiceTemplateService
      .listTemplates()
      .then(setTemplates)
      .catch(() => toast.error("Failed to load templates"))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold mb-1">Start from a template</h3>
        <p className="text-sm text-muted-foreground">
          Pick an industry template to pre-fill your agent configuration, or skip to set it up manually.
        </p>
      </div>

      {loading ? (
        <div className="flex justify-center py-8">
          <Loader2 className="w-7 h-7 animate-spin text-primary" />
        </div>
      ) : (
        <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
          {templates.map((t) => {
            const isSelected = selected?.id === t.id;
            return (
              <div
                key={t.id}
                onClick={() => setSelected(t)}
                className={cn(
                  "p-3 border-2 rounded-lg cursor-pointer transition-all",
                  isSelected
                    ? "border-primary bg-primary/5"
                    : "border-border hover:border-primary/40 hover:bg-muted/40",
                )}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-medium text-sm text-foreground">{t.name}</span>
                      <Badge variant="secondary" className="text-xs capitalize">{t.industry.replace("_", " ")}</Badge>
                      {isSelected && <CheckCircle2 className="w-4 h-4 text-primary" />}
                    </div>
                    {t.description && (
                      <p className="text-xs text-muted-foreground mt-0.5 line-clamp-1">{t.description}</p>
                    )}
                    {t.tone && (
                      <p className="text-xs text-muted-foreground/70 mt-0.5">Tone: {t.tone}</p>
                    )}
                  </div>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="shrink-0 h-7 text-xs"
                    onClick={(e) => {
                      e.stopPropagation();
                      setPreview(preview?.id === t.id ? null : t);
                    }}
                  >
                    <Eye className="w-3 h-3 mr-1" />
                    {preview?.id === t.id ? "Hide" : "Preview"}
                  </Button>
                </div>
                {preview?.id === t.id && (
                  <div className="mt-2 pt-2 border-t border-border/60 space-y-1">
                    {t.greeting && (
                      <p className="text-xs text-foreground/80">
                        <span className="font-medium">Greeting:</span> {t.greeting.replace("[Business Name]", "Your Business")}
                      </p>
                    )}
                    {t.mission && (
                      <p className="text-xs text-muted-foreground">
                        <span className="font-medium">Mission:</span> {t.mission}
                      </p>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      <div className="flex gap-3 pt-2 border-t">
        <Button
          type="button"
          variant="outline"
          onClick={onSkip}
          className="flex-1"
        >
          <SkipForward className="w-4 h-4 mr-2" />
          Skip — set up manually
        </Button>
        <Button
          type="button"
          disabled={!selected}
          onClick={() => selected && onSelect(selected)}
          className="flex-1"
        >
          Use Template
          <ChevronRight className="w-4 h-4 ml-2" />
        </Button>
      </div>
    </div>
  );
}

export function AgentCreateWidget() {
  const searchParams = useSearchParams();
  const { organizations, currentOrganization } = useOrganization();
  const createAgentMutation = useCreateAgent();
  const [currentStage, setCurrentStage] = useState<Stage>("template");
  const [createdAgent, setCreatedAgent] = useState<{
    id: string;
    name: string;
  } | null>(null);

  const form = useForm<FormData>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      organization_id: currentOrganization?.id || "",
      name: "",
      phone_number: "",
      persona: "",
      tone: "Professional",
      mission: "",
      custom_instructions: "",
      is_active: true,
      preset_id: null,
    },
  });

  const watchedOrgId = form.watch("organization_id");
  const { data: presetCatalog } = usePresetCatalog({
    organizationId: watchedOrgId || null,
  });

  useEffect(() => {
    const orgIdFromParams = searchParams.get("org_id");
    if (orgIdFromParams && organizations) {
      const orgExists = organizations.some((org) => org.id === orgIdFromParams);
      if (orgExists) {
        form.setValue("organization_id", orgIdFromParams);
      }
    }
  }, [searchParams, organizations, form]);

  const stages: Stage[] = ["template", "basic", "phone", "tools", "review"];
  const indicatorStages: Stage[] =
    currentStage === "success" ? [...stages, "success"] : stages;
  const currentIndex = stages.indexOf(currentStage);
  const isFirstStage = currentIndex === 0;
  const isLastStage = currentStage === "review";
  const isSuccessStage = currentStage === "success";

  const handleTemplateSelect = (template: VoiceTemplate) => {
    form.setValue("persona", template.persona ?? "");
    form.setValue("tone", template.tone ?? "Professional");
    form.setValue("mission", template.mission ?? "");
    const instructions = [
      template.custom_instructions,
      template.greeting ? `Default greeting: ${template.greeting}` : null,
    ]
      .filter(Boolean)
      .join("\n\n");
    form.setValue("custom_instructions", instructions);
    setCurrentStage("basic");
  };

  const validateCurrentStage = async (): Promise<boolean> => {
    const fieldsToValidate: Record<Stage, (keyof FormData)[]> = {
      template: [],
      basic: ["organization_id", "name", "persona", "tone", "mission"],
      // Phone is optional; still validate format when a value is entered.
      phone: ["phone_number"],
      tools: [],
      review: [],
      success: [],
    };

    const fields = fieldsToValidate[currentStage];

    if (fields.length === 0) {
      return true;
    }

    const results = await Promise.all(
      fields.map((field) =>
        form.trigger(field as Parameters<typeof form.trigger>[0]),
      ),
    );

    return results.every((result) => result === true);
  };

  const handleSkipPhone = () => {
    form.setValue("phone_number", "", { shouldValidate: true });
    setCurrentStage("tools");
  };

  const handleNext = async (e?: React.MouseEvent) => {
    if (e) {
      e.preventDefault();
    }

    const isValid = await validateCurrentStage();
    if (!isValid) {
      return;
    }

    if (!isLastStage) {
      setCurrentStage(stages[currentIndex + 1]);
    }
  };

  const handleBack = (e?: React.MouseEvent) => {
    if (e) {
      e.preventDefault();
    }

    if (!isFirstStage) {
      setCurrentStage(stages[currentIndex - 1]);
    }
  };

  const handleSubmit = async (data: FormData) => {
    if (currentStage !== "review") {
      return;
    }

    try {
      const selectedOrg = organizations?.find(
        (org) => org.id === data.organization_id,
      );
      const resolvedPromptFields = resolveAgentCreatePromptFields(
        {
          persona: data.persona,
          mission: data.mission,
          custom_instructions: data.custom_instructions,
        },
        {
          businessName: selectedOrg?.name ?? "",
          agentName: data.name,
        },
      );

      const payload: VoiceAgentCreate = {
        ...data,
        ...resolvedPromptFields,
        phone_number: normalizeOptionalPhone(data.phone_number),
      };
      const agent = await createAgentMutation.mutateAsync(payload);
      setCreatedAgent({ id: agent.id, name: agent.name || data.name });
      setCurrentStage("success");
      toast.success("Agent created successfully!");
    } catch (error) {
      console.error("Failed to create agent:", error);
    }
  };

  const renderBasicStage = () => (
    <div className="space-y-6">
      <div className="bg-blue-50 border border-blue-200 rounded-md p-3 flex items-start gap-2">
        <Info className="h-4 w-4 text-blue-600 mt-0.5 flex-shrink-0" />
        <p className="text-sm text-blue-800">
          The information you provide here helps the AI agent represent your business accurately when speaking with callers.
        </p>
      </div>

      <div>
        <h3 className="text-lg font-semibold mb-2">Basic Information</h3>
        <p className="text-sm text-muted-foreground">
          Enter the basic details for your voice agent
        </p>
      </div>

      <FormField
        control={form.control}
        name="organization_id"
        render={({ field }) => (
          <FormItem>
            <FormLabel>Organization *</FormLabel>
            <FormControl>
              <select
                {...field}
                className="w-full px-3 py-2.5 border border-input bg-background rounded-md focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
              >
                <option value="">Select an organization</option>
                {organizations?.map((org) => (
                  <option key={org.id} value={org.id}>
                    {org.name}
                  </option>
                ))}
              </select>
            </FormControl>
            <FormMessage />
          </FormItem>
        )}
      />

      <FormField
        control={form.control}
        name="name"
        render={({ field }) => (
          <FormItem>
            <FormLabel>Agent Name *</FormLabel>
            <FormControl>
              <Input {...field} placeholder="Support Agent, Sales Bot, etc." />
            </FormControl>
            <FormMessage />
          </FormItem>
        )}
      />

      <div className="grid grid-cols-2 gap-4">
        <FormField
          control={form.control}
          name="persona"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Agent Persona / Role *</FormLabel>
              <FormControl>
                <Input {...field} placeholder="Front Desk Coordinator" />
              </FormControl>
              <FormDescription>The character or job title</FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="tone"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Communication Tone *</FormLabel>
              <FormControl>
                <select
                  {...field}
                  className="w-full px-3 py-2 border border-input bg-background rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                >
                  <option value="Professional">Professional</option>
                  <option value="Friendly">Friendly</option>
                  <option value="Enthusiastic">Enthusiastic</option>
                  <option value="Minimalist">Minimalist / Formal</option>
                </select>
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
      </div>

      <FormField
        control={form.control}
        name="mission"
        render={({ field }) => (
          <FormItem>
            <FormLabel>Key Mission *</FormLabel>
            <FormControl>
              <Textarea
                {...field}
                placeholder="e.g., Your main goal is to book appointments and answer pricing questions."
                className="min-h-[80px]"
              />
            </FormControl>
            <FormDescription>What should the agent accomplish?</FormDescription>
            <FormMessage />
          </FormItem>
        )}
      />

      <FormField
        control={form.control}
        name="custom_instructions"
        render={({ field }) => (
          <FormItem>
            <FormLabel>Additional Instructions</FormLabel>
            <FormControl>
              <Textarea
                {...field}
                placeholder={`Add context specific to this agent's role. Include:

• Company policies and procedures (for support agents)
• Unique selling points and differentiators (for sales agents)
• Common customer questions and how to handle them
• Emergency or after-hours protocols
• Specific workflows or escalation procedures
• Any other context that helps this agent handle calls effectively

Example: "Always mention our 30-day guarantee. For pricing questions, emphasize competitive rates. For enterprise inquiries, gather company size before scheduling a demo."`}
                className="min-h-[150px]"
              />
            </FormControl>
            <FormDescription>Role-specific context and instructions</FormDescription>
            <FormMessage />
          </FormItem>
        )}
      />

      <FormField
        control={form.control}
        name="is_active"
        render={({ field }) => (
          <FormItem className="flex flex-row items-start space-x-3 space-y-0">
            <FormControl>
              <Checkbox
                checked={field.value}
                onCheckedChange={field.onChange}
              />
            </FormControl>
            <div className="space-y-1 leading-none">
              <FormLabel>Agent is active</FormLabel>
              <FormDescription>
                The agent will be ready to handle calls immediately
              </FormDescription>
            </div>
          </FormItem>
        )}
      />

      {/* Voice profile (Phase 4). Optional — null = system default. The
          picker emits null for the default so the backend never sees "" (which
          would fail UUID validation). */}
      <FormField
        control={form.control}
        name="preset_id"
        render={({ field }) => (
          <FormItem>
            <FormControl>
              {watchedOrgId ? (
                <PresetPicker
                  organizationId={watchedOrgId}
                  value={field.value ?? null}
                  onChange={field.onChange}
                />
              ) : (
                <p className="text-xs text-muted-foreground">
                  Select an organization above to choose a voice profile.
                </p>
              )}
            </FormControl>
            <FormMessage />
          </FormItem>
        )}
      />
    </div>
  );

  const renderReviewStage = () => {
    const values = form.watch();

    const orgName = organizations?.find(
      (o) => o.id === values.organization_id,
    )?.name;

    // Resolve the chosen preset's name for the review summary. null/unknown ->
    // DEFAULT_PRESET_DISPLAY (the same "System Default" label the platform admin
    // sees on /platform/presets and the picker shows; the underlying engine is
    // not surfaced here).
    const presetName = values.preset_id
      ? (presetCatalog?.presets.find((p) => p.id === values.preset_id)?.name ??
        "Selected profile")
      : DEFAULT_PRESET_DISPLAY.name;

    return (
      <div className="space-y-6">
        <div>
          <h3 className="text-lg font-semibold mb-2">Review & Create</h3>
          <p className="text-sm text-muted-foreground">
            Review your agent configuration before creating it
          </p>
        </div>

        <div className="space-y-4">
          <Card className="p-4">
            <div className="space-y-3">
              <div>
                <span className="text-xs text-muted-foreground uppercase tracking-wide">
                  Organization
                </span>
                <p className="font-medium mt-1">{orgName || "Not selected"}</p>
              </div>
              <div>
                <span className="text-xs text-muted-foreground uppercase tracking-wide">
                  Agent Name
                </span>
                <p className="font-medium mt-1">{values.name || "Not set"}</p>
              </div>
              <div>
                <span className="text-xs text-muted-foreground uppercase tracking-wide">
                  Phone Number
                </span>
                <p className="font-medium mt-1">
                  {values.phone_number?.trim() || "Not configured (optional)"}
                </p>
              </div>
              <div>
                <span className="text-xs text-muted-foreground uppercase tracking-wide">
                  Persona
                </span>
                <p className="font-medium mt-1">
                  {values.persona || "Not set"}
                </p>
              </div>
              <div>
                <span className="text-xs text-muted-foreground uppercase tracking-wide">
                  Tone
                </span>
                <p className="font-medium mt-1">{values.tone}</p>
              </div>
              <div>
                <span className="text-xs text-muted-foreground uppercase tracking-wide">
                  Mission
                </span>
                <p className="text-sm mt-1 text-muted-foreground line-clamp-2">
                  {values.mission || "Not set"}
                </p>
              </div>
              <div>
                <span className="text-xs text-muted-foreground uppercase tracking-wide">
                  Voice Profile
                </span>
                <p className="font-medium mt-1">{presetName}</p>
              </div>
              <div>
                <span className="text-xs text-muted-foreground uppercase tracking-wide">
                  Status
                </span>
                <div className="flex items-center mt-1">
                  <div
                    className={cn(
                      "w-2 h-2 rounded-full mr-2",
                      values.is_active ? "bg-green-500" : "bg-gray-400",
                    )}
                  />
                  <span className="text-sm font-medium">
                    {values.is_active ? "Active" : "Inactive"}
                  </span>
                </div>
              </div>
            </div>
          </Card>
        </div>
      </div>
    );
  };

  return (
    <div className="max-w-2xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold">Create New Voice Agent</h1>
        <p className="text-muted-foreground mt-1">
          Set up your AI voice agent in a few simple steps
        </p>
      </div>

      <Card className="p-6">
        {!isSuccessStage && (
          <StepIndicator stages={indicatorStages} currentStage={currentStage} />
        )}

        {isSuccessStage && createdAgent ? (
          <AgentCreateSuccess
            agentId={createdAgent.id}
            agentName={createdAgent.name}
          />
        ) : (
          <Form {...form}>
            <form
              onSubmit={form.handleSubmit(handleSubmit)}
              className="space-y-6"
            >
              {currentStage === "template" && (
                <TemplateSelectionStage
                  onSelect={handleTemplateSelect}
                  onSkip={() => setCurrentStage("basic")}
                />
              )}
              {currentStage === "basic" && renderBasicStage()}
              {currentStage === "phone" && (
                <AgentCreatePhoneStage
                  control={form.control}
                  onSkip={handleSkipPhone}
                />
              )}
              {currentStage === "tools" && <AgentCreateToolsStage />}
              {currentStage === "review" && renderReviewStage()}

              {currentStage !== "template" && (
                <div className="flex items-center justify-between pt-6 border-t">
                  <Button
                    type="button"
                    variant="outline"
                    onClick={handleBack}
                    disabled={isFirstStage}
                  >
                    <ChevronLeft className="h-4 w-4 mr-2" />
                    Back
                  </Button>

                  <div className="flex items-center gap-2">
                    {isLastStage ? (
                      <Button
                        type="submit"
                        disabled={createAgentMutation.isPending}
                      >
                        {createAgentMutation.isPending ? (
                          <>Creating...</>
                        ) : (
                          <>
                            Create Agent
                            <Check className="h-4 w-4 ml-2" />
                          </>
                        )}
                      </Button>
                    ) : (
                      <Button type="button" onClick={handleNext}>
                        Next Step
                        <ChevronRight className="h-4 w-4 ml-2" />
                      </Button>
                    )}
                  </div>
                </div>
              )}
            </form>
          </Form>
        )}
      </Card>
    </div>
  );
}
