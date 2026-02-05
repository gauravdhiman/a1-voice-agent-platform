"use client";

import React, { useState, useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { useRouter, useSearchParams } from "next/navigation";
import { useOrganization } from "@/contexts/organization-context";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Bot, Phone, ChevronRight, ChevronLeft, Check, Info } from "lucide-react";
import { useCreateAgent } from "@/hooks/use-agent-queries";
import { toast } from "sonner";
import type { VoiceAgentCreate } from "@/types/agent";
import { cn } from "@/lib/utils";

const formSchema = z.object({
  organization_id: z.string().min(1, "Organization is required"),
  name: z.string().min(1, "Agent name is required"),
  phone_number: z
    .string()
    .min(1, "Phone number is required")
    .regex(
      /^\+[1-9]\d{7,14}$/,
      "Phone number must be in E.164 format with at least 8 digits (e.g., +14155551234 or +441632960000)",
    ),
  persona: z.string().min(1, "Persona is required"),
  tone: z.string().min(1, "Tone is required"),
  mission: z.string().min(1, "Mission is required"),
  custom_instructions: z.string().optional(),
  is_active: z.boolean(),
});

type FormData = z.infer<typeof formSchema>;

type Stage = "basic" | "phone" | "tools" | "review";

const stageConfig = {
  basic: { step: 1, title: "Basic Information", icon: Bot },
  phone: { step: 2, title: "Phone Number", icon: Phone },
  tools: { step: 3, title: "Platform Tools", icon: Check },
  review: { step: 4, title: "Review & Create", icon: Check },
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

export function AgentCreateWidget() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { organizations, currentOrganization } = useOrganization();
  const createAgentMutation = useCreateAgent();
  const [currentStage, setCurrentStage] = useState<Stage>("basic");

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
    },
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

  const stages: Stage[] = ["basic", "phone", "tools", "review"];
  const currentIndex = stages.indexOf(currentStage);
  const isFirstStage = currentIndex === 0;
  const isLastStage = currentIndex === stages.length - 1;

  const validateCurrentStage = async (): Promise<boolean> => {
    const fieldsToValidate: Record<Stage, (keyof FormData)[]> = {
      basic: ["organization_id", "name", "persona", "tone", "mission"],
      phone: ["phone_number"],
      tools: [],
      review: [],
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
      const createdAgent = await createAgentMutation.mutateAsync(
        data as VoiceAgentCreate,
      );
      toast.success("Agent created successfully!");
      router.push(`/agents/${createdAgent.id}?tab=tools`);
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
    </div>
  );

  const renderPhoneStage = () => (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold mb-2">Phone Number</h3>
        <p className="text-sm text-muted-foreground">
          Configure the phone number for your voice agent. Enter an existing
          phone number in E.164 format.
        </p>
      </div>

      <FormField
        control={form.control}
        name="phone_number"
        render={({ field }) => (
          <FormItem>
            <FormLabel>Phone Number *</FormLabel>
            <FormControl>
              <Input {...field} placeholder="+1234567890" />
            </FormControl>
            <FormDescription>
              Enter a phone number in E.164 format (e.g., +1234567890)
            </FormDescription>
            <FormMessage />
          </FormItem>
        )}
      />

      <div className="bg-muted/30 rounded-lg p-4 border border-dashed">
        <p className="text-sm text-muted-foreground">
          <span className="font-medium">Coming Soon:</span> Search and purchase
          phone numbers directly through our platform.
        </p>
      </div>
    </div>
  );

  const renderToolsStage = () => (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold mb-2">Platform Tools</h3>
        <p className="text-sm text-muted-foreground">
          Configure tools that your agent can use to interact with external
          services and APIs.
        </p>
      </div>

      <div className="bg-muted/30 rounded-lg p-8 text-center border border-dashed">
        <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-primary/10 mb-4">
          <Check className="h-6 w-6 text-primary" />
        </div>
        <h4 className="font-semibold mb-2">Tools Configuration</h4>
        <p className="text-sm text-muted-foreground mb-4 max-w-md mx-auto">
          You can configure platform tools after creating the agent. This
          feature allows your agent to integrate with external services like
          calendars, databases, and APIs.
        </p>
        <p className="text-sm text-primary font-medium mb-2 max-w-md mx-auto">
          You can move on and configure tools later from the agent configuration
          page.
        </p>
      </div>
    </div>
  );

  const renderReviewStage = () => {
    const values = form.watch();

    const orgName = organizations?.find(
      (o) => o.id === values.organization_id,
    )?.name;

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
                  {values.phone_number || "Not configured"}
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
        <StepIndicator stages={stages} currentStage={currentStage} />

        <Form {...form}>
          <form
            onSubmit={form.handleSubmit(handleSubmit)}
            className="space-y-6"
          >
            {currentStage === "basic" && renderBasicStage()}
            {currentStage === "phone" && renderPhoneStage()}
            {currentStage === "tools" && renderToolsStage()}
            {currentStage === "review" && renderReviewStage()}

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
          </form>
        </Form>
      </Card>
    </div>
  );
}
