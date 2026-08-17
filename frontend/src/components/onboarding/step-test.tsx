"use client";

import { useEffect, useState } from "react";
import { CheckCircle2, Loader2, Mic, Phone } from "lucide-react";
import { toast } from "sonner";
import { TestCallModal } from "@/components/agents/test-call-modal";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  applyTemplatePlaceholders,
  suggestAgentName,
  type OnboardingWizardState,
} from "@/lib/onboarding";
import { agentService } from "@/services/agent-service";
import { organizationService } from "@/services/organization-service";

export interface StepTestProps {
  state: OnboardingWizardState;
  orgId: string;
  onChange: (update: Partial<OnboardingWizardState>) => void;
  /** Called after onboarding is marked complete (agent created or finish clicked) */
  onOnboardingCompleted: () => void;
  onComplete: () => void;
}

interface OnboardingAgentCreationResult {
  agentId: string;
  onboardingCompleted: boolean;
}

/**
 * In-flight / completed agent creation promises keyed by organization id.
 *
 * Module scope is required so React Strict Mode remounts (dev) share one create
 * call instead of creating duplicate agents.
 */
const onboardingAgentCreationByOrg = new Map<
  string,
  Promise<OnboardingAgentCreationResult>
>();

/**
 * Clear the module-level creation cache (tests only).
 */
export function resetOnboardingAgentCreationForTests(): void {
  onboardingAgentCreationByOrg.clear();
}

/**
 * Build create-agent payload and instructions from wizard state.
 *
 * @param state Wizard state from earlier onboarding steps
 * @param orgId Organization that will own the agent
 * @param agentName Resolved display name for the agent
 */
function buildCreateAgentRequest(
  state: OnboardingWizardState,
  orgId: string,
  agentName: string,
) {
  const template = state.selectedTemplate;
  const businessContext = state.businessDescription
    ? `Business: ${state.businessName}\nLocation: ${state.location}\n\n${state.businessDescription}`
    : `Business: ${state.businessName}\nLocation: ${state.location}`;

  const markdownSections: string[] = [];

  if (template) {
    const persona = applyTemplatePlaceholders(template.persona, {
      businessName: state.businessName,
      agentName,
    });
    const greeting = applyTemplatePlaceholders(template.greeting, {
      businessName: state.businessName,
      agentName,
    });

    if (persona) {
      markdownSections.push(`# Identity and Persona\n\n${persona}`);
    }
    if (template.tone) {
      markdownSections.push(`Your communication style is ${template.tone}.`);
    }
    if (template.mission) {
      markdownSections.push(`# Mission\n\n${template.mission}`);
    }
    markdownSections.push(`# Business Context\n\n${businessContext}`);
    if (greeting) {
      markdownSections.push(`# Default Greeting\n\n${greeting}`);
    }
    if (template.custom_instructions) {
      markdownSections.push(`# Instructions\n\n${template.custom_instructions}`);
    }
  } else {
    markdownSections.push(
      `# Identity and Persona\n\nYou are ${agentName}, a helpful phone receptionist for ${state.businessName || "the business"}.`,
    );
    markdownSections.push(`# Business Context\n\n${businessContext}`);
    markdownSections.push(
      `# Default Greeting\n\nThank you for calling ${state.businessName || "us"}! This is ${agentName}, how can I help you today?`,
    );
  }

  return {
    organization_id: orgId,
    name: agentName,
    phone_number: state.purchasedPhoneNumber ?? undefined,
    persona: template
      ? applyTemplatePlaceholders(template.persona, {
          businessName: state.businessName,
          agentName,
        }) || undefined
      : undefined,
    tone: template?.tone ?? undefined,
    mission: template?.mission ?? undefined,
    custom_instructions: template?.custom_instructions ?? undefined,
    instructions_markdown: markdownSections.join("\n\n"),
    is_active: true,
  };
}

/**
 * Create the onboarding agent at most once per organization (shared promise).
 *
 * If agent creation succeeds but completing onboarding fails, the agent id is
 * still cached so a remount/retry will not create a second agent.
 *
 * @param orgId Organization id used as the dedupe key
 * @param state Wizard state for agent content
 * @param agentName Display name for the agent
 * @returns Created agent id and whether onboarding was persisted
 */
async function createOnboardingAgentOnce(
  orgId: string,
  state: OnboardingWizardState,
  agentName: string,
): Promise<OnboardingAgentCreationResult> {
  const existing = onboardingAgentCreationByOrg.get(orgId);
  if (existing) {
    return existing;
  }

  // Register the gate promise synchronously before any await so concurrent
  // Strict Mode effect runs share one in-flight creation.
  let resolveGate!: (value: OnboardingAgentCreationResult) => void;
  let rejectGate!: (reason?: unknown) => void;
  const gate = new Promise<OnboardingAgentCreationResult>((resolve, reject) => {
    resolveGate = resolve;
    rejectGate = reject;
  });
  onboardingAgentCreationByOrg.set(orgId, gate);

  void (async () => {
    try {
      const agent = await agentService.createAgent(
        buildCreateAgentRequest(state, orgId, agentName),
      );
      try {
        await organizationService.completeOnboarding(orgId);
        resolveGate({ agentId: agent.id, onboardingCompleted: true });
      } catch {
        // Keep the agent id cached; finish/retry can re-attempt complete only.
        resolveGate({ agentId: agent.id, onboardingCompleted: false });
      }
    } catch (error) {
      onboardingAgentCreationByOrg.delete(orgId);
      rejectGate(error);
    }
  })();

  return gate;
}

/**
 * Step 5 — create the agent, optional test call, then go to the dashboard.
 *
 * There is no Back control: once the user reaches this step the agent is being
 * (or has been) created. On successful creation we also mark onboarding
 * complete so a page refresh lands on the dashboard.
 */
export function StepTest({
  state,
  orgId,
  onChange,
  onOnboardingCompleted,
  onComplete,
}: StepTestProps) {
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [agentId, setAgentId] = useState<string | null>(state.createdAgentId);
  const [testCallOpen, setTestCallOpen] = useState(false);
  const [completing, setCompleting] = useState(false);

  const displayAgentName =
    state.agentName.trim() ||
    suggestAgentName(state.businessName) ||
    "Your AI Agent";

  useEffect(() => {
    if (agentId) return;

    let cancelled = false;

    const run = async () => {
      setCreating(true);
      setCreateError(null);
      try {
        const result = await createOnboardingAgentOnce(
          orgId,
          state,
          displayAgentName,
        );
        if (cancelled) return;
        setAgentId(result.agentId);
        onChange({ createdAgentId: result.agentId });
        // Always mark complete locally so refresh doesn't bounce back here.
        onOnboardingCompleted();
        if (!result.onboardingCompleted) {
          toast.error(
            "Agent created, but we couldn't save onboarding status yet.",
          );
        }
      } catch (err) {
        if (cancelled) return;
        const msg =
          err instanceof Error ? err.message : "Failed to create agent";
        setCreateError(msg);
        toast.error(msg);
      } finally {
        if (!cancelled) {
          setCreating(false);
        }
      }
    };

    void run();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleFinish = async () => {
    setCompleting(true);
    try {
      await organizationService.completeOnboarding(orgId);
      onOnboardingCompleted();
      onComplete();
    } catch {
      toast.error("Failed to save progress, but your setup is complete.");
      onOnboardingCompleted();
      onComplete();
    } finally {
      setCompleting(false);
    }
  };

  const isReady = !!agentId;

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">
          {creating
            ? "Almost done — setting up your agent"
            : isReady
              ? "Your agent is ready!"
              : "Test your AI agent"}
        </h2>
        <p className="text-gray-500 mt-1">
          {creating
            ? "Creating your AI agent, this will only take a moment..."
            : isReady
              ? "Make a quick test call from your browser to hear it in action."
              : createError
                ? "There was an issue creating your agent. You can retry or continue to your dashboard."
                : "Your agent will be set up automatically."}
        </p>
      </div>

      <div className="p-6 bg-blue-50 border border-blue-200 rounded-xl text-center space-y-4">
        <div className="w-16 h-16 bg-blue-600 rounded-full flex items-center justify-center mx-auto">
          {creating ? (
            <Loader2 className="w-8 h-8 text-white animate-spin" />
          ) : (
            <Mic className="w-8 h-8 text-white" />
          )}
        </div>
        <div>
          <p className="font-semibold text-gray-900 text-lg">
            {displayAgentName}
          </p>
          <p className="text-sm text-gray-500">
            {state.selectedTemplate
              ? `${state.businessName} · ${state.selectedTemplate.name}`
              : state.businessName}
          </p>
        </div>
        {isReady && (
          <Button
            onClick={() => setTestCallOpen(true)}
            size="lg"
            className="px-8"
          >
            <Phone className="w-4 h-4 mr-2" /> Start test call
          </Button>
        )}
        {creating && (
          <p className="text-sm text-blue-600">Setting up your agent...</p>
        )}
      </div>

      {isReady && (
        <Alert className="border-green-200 bg-green-50">
          <CheckCircle2 className="w-4 h-4 text-green-600" />
          <AlertDescription className="text-green-700 ml-2">
            Agent created successfully! You can test call it or go to your
            dashboard.
            {!state.purchasedPhoneNumber && (
              <span className="block mt-1 text-xs text-green-600">
                Note: no phone number configured — inbound calls will not work
                until you add one from Settings.
              </span>
            )}
          </AlertDescription>
        </Alert>
      )}

      {createError && (
        <Alert className="border-red-200 bg-red-50">
          <AlertDescription className="text-red-700 ml-2">
            {createError} — you can still continue to your dashboard and set up
            your agent there.
          </AlertDescription>
        </Alert>
      )}

      <Button
        onClick={handleFinish}
        className="w-full"
        size="lg"
        disabled={completing || creating}
        data-testid="onboarding-go-dashboard"
      >
        {completing ? (
          <>
            <Loader2 className="w-4 h-4 mr-2 animate-spin" /> Finishing...
          </>
        ) : (
          <>
            <CheckCircle2 className="w-4 h-4 mr-2" /> Go to Dashboard
          </>
        )}
      </Button>

      {agentId && (
        <TestCallModal
          open={testCallOpen}
          onOpenChange={setTestCallOpen}
          agentId={agentId}
          agentName={displayAgentName}
        />
      )}
    </div>
  );
}
