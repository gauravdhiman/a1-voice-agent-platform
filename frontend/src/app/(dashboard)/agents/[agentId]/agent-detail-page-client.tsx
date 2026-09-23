"use client";

import React, { useCallback, useEffect } from "react";
import dynamic from "next/dynamic";
import { toast } from "sonner";
import { ArrowLeft, Bot, Loader2, Phone } from "lucide-react";

import { useAuth } from "@/contexts/auth-context";
import { useUserPermissions } from "@/hooks/use-user-permissions";
import { useCallLogs } from "@/hooks/use-call-logs";
import {
  useAgent,
  useDeleteAgent,
  useUpdateAgent,
} from "@/hooks/use-agent-queries";
import { organizationService } from "@/services/organization-service";
import { agentService } from "@/services/agent-service";
import type { Organization } from "@/types/organization";
import type { PhoneNumberWithAgent } from "@/types/phone-number";
import type { VoiceAgent, VoiceAgentUpdate } from "@/types/agent";
import {
  getAgentDetailHref,
  normalizeAgentDetailTab,
  shouldShowAgentRecordingsTab,
} from "@/components/agents/agent-detail-tabs";
import { useSelectedPresetReadiness } from "@/components/agents/preset-picker";
import { PresetSetupCallout } from "@/components/agents/preset-setup-callout";
import { AgentDetailSaveBar } from "@/components/agents/agent-detail-save-bar";
import { DeleteButton } from "@/components/ui/delete-button";
import { Button } from "@/components/ui/button";
import {
  AnimatedTabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import { buildAgentInstructionsMarkdown } from "@/lib/agent-instructions";
import {
  useRouter,
  useParams,
  useSelectedLayoutSegment,
} from "next/navigation";

import type { AgentDetailFormState } from "./agent-detail-types";

const AgentDeleteDialog = dynamic(
  () =>
    import("@/components/agents/agent-delete-dialog").then(
      (module) => module.AgentDeleteDialog,
    ),
  { ssr: false },
);
const TestCallModal = dynamic(
  () =>
    import("@/components/agents/test-call-modal").then(
      (module) => module.TestCallModal,
    ),
  { ssr: false },
);
const EmbedButtonConfig = dynamic(
  () =>
    import("@/components/agents/embed-button-config").then(
      (module) => module.EmbedButtonConfig,
    ),
  { ssr: false },
);

const INITIAL_AGENT_FORM: AgentDetailFormState = {
  name: "",
  persona: "",
  tone: "",
  is_active: true,
  is_published_on_public_page: false,
  call_recording_enabled: false,
  use_platform_credits: false,
  instructions_markdown: "",
  preset_id: null,
  is_demo: false,
  demo_slug: "",
  public_description: "",
  demo_public_result_url: "",
  demo_calls_remaining: -1,
  demo_max_call_duration_minutes: -1,
};

/**
 * Coordinates the agent-detail shell and its release-critical mutations.
 * Each route supplies only its active tab renderer, keeping feature-heavy
 * tabs out of the initial route's module graph.
 */
export interface AgentDetailPageRenderContext {
  agent: VoiceAgent;
  organization: Organization | null;
  agentForm: AgentDetailFormState;
  setAgentForm: React.Dispatch<React.SetStateAction<AgentDetailFormState>>;
  canEdit: boolean;
  isPlatformAdmin: boolean;
  assignedPhoneNumber: PhoneNumberWithAgent | null;
  setAssignedPhoneNumber: React.Dispatch<
    React.SetStateAction<PhoneNumberWithAgent | null>
  >;
}

const AgentDetailPageContext = React.createContext<
  AgentDetailPageRenderContext | undefined
>(undefined);

/** Returns the persistent agent-detail state for the active tab route. */
export function useAgentDetailPage(): AgentDetailPageRenderContext {
  const context = React.useContext(AgentDetailPageContext);
  if (!context) {
    throw new Error(
      "useAgentDetailPage must be used inside the agent detail layout",
    );
  }
  return context;
}

interface AgentDetailPageProps {
  children: React.ReactNode;
}

export default function AgentDetailPage({ children }: AgentDetailPageProps) {
  const { user } = useAuth();
  const { isPlatformAdmin } = useUserPermissions();
  const router = useRouter();
  const params = useParams();
  const selectedLayoutSegment = useSelectedLayoutSegment();
  const activeTab = normalizeAgentDetailTab(selectedLayoutSegment);
  const agentId = params.agentId as string;

  const [organization, setOrganization] = React.useState<Organization | null>(
    null,
  );
  const [assignedPhoneNumber, setAssignedPhoneNumber] =
    React.useState<PhoneNumberWithAgent | null>(null);
  const [saving, setSaving] = React.useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = React.useState(false);
  const [testCallOpen, setTestCallOpen] = React.useState(false);
  const [agentForm, setAgentForm] =
    React.useState<AgentDetailFormState>(INITIAL_AGENT_FORM);

  const {
    data: agent,
    isLoading: agentLoading,
    error: agentError,
  } = useAgent(agentId);

  const canViewRecordings =
    isPlatformAdmin ||
    Boolean(agent && user?.hasRole("org_admin", agent.organization_id));
  const { data: agentRecordingSummary, isLoading: recordingsLoading } =
    useCallLogs(
      agent?.organization_id ?? "",
      {
        agent_id: agentId,
        recording_only: true,
        page: 1,
        page_size: 1,
      },
      canViewRecordings,
    );
  const recordingsTabVisible = shouldShowAgentRecordingsTab(
    Boolean(agent?.call_recording_enabled),
    Boolean(agentRecordingSummary?.total),
    canViewRecordings,
  );

  const updateAgentMutation = useUpdateAgent();
  const deleteAgentMutation = useDeleteAgent();
  const {
    isReady: voiceProfileReady,
    isLoading: voiceProfileReadinessLoading,
    credentialsSelfService,
  } = useSelectedPresetReadiness(
    agent?.organization_id,
    agentForm.preset_id,
    agentForm.use_platform_credits,
  );

  React.useEffect(() => {
    if (!agent?.organization_id) return;
    organizationService
      .getOrganizationById(agent.organization_id)
      .then(setOrganization)
      .catch((error) => {
        console.error("Failed to load organization:", error);
      });
  }, [agent?.organization_id]);

  React.useEffect(() => {
    if (!agent) return;

    let cancelled = false;
    setAgentForm({
      name: agent.name,
      persona: agent.persona || "",
      tone: agent.tone || "",
      is_active: agent.is_active,
      is_published_on_public_page: agent.is_published_on_public_page ?? false,
      call_recording_enabled: agent.call_recording_enabled ?? false,
      use_platform_credits: agent.use_platform_credits || false,
      instructions_markdown: agent.instructions_markdown || "",
      preset_id: agent.preset_id ?? null,
      is_demo: Boolean(agent.is_demo),
      demo_slug: agent.demo_slug || "",
      public_description: agent.public_description || "",
      demo_public_result_url: agent.demo_public_result_url || "",
      demo_calls_remaining: agent.demo_calls_remaining ?? -1,
      demo_max_call_duration_minutes:
        agent.demo_max_call_duration_seconds == null ||
        agent.demo_max_call_duration_seconds === -1
          ? -1
          : Math.max(1, Math.round(agent.demo_max_call_duration_seconds / 60)),
    });

    if (!agent.instructions_markdown?.trim()) {
      agentService
        .generateMarkdown(agent.id)
        .then((markdown) => {
          if (!cancelled && markdown.trim()) {
            setAgentForm((current) =>
              current.instructions_markdown.trim()
                ? current
                : { ...current, instructions_markdown: markdown },
            );
          }
        })
        .catch(() => {
          // Keep the placeholder available when legacy Markdown generation fails.
        });
    }

    return () => {
      cancelled = true;
    };
  }, [agent]);

  const handleTabChange = useCallback(
    (value: string) => {
      const tab = normalizeAgentDetailTab(value);
      router.push(getAgentDetailHref(agentId, tab), { scroll: false });
    },
    [agentId, router],
  );

  useEffect(() => {
    if (
      activeTab === "recordings" &&
      !recordingsLoading &&
      !recordingsTabVisible
    ) {
      router.replace(getAgentDetailHref(agentId), { scroll: false });
    }
  }, [activeTab, agentId, recordingsLoading, recordingsTabVisible, router]);

  const handleSaveAgent = useCallback(async () => {
    if (!agentId) return;

    if (isPlatformAdmin && agentForm.is_demo && !agentForm.demo_slug.trim()) {
      toast.error("Demo slug is required when demo is enabled");
      return;
    }
    if (
      isPlatformAdmin &&
      agentForm.is_demo &&
      !/^[a-z0-9-]+$/.test(agentForm.demo_slug.trim().toLowerCase())
    ) {
      toast.error(
        "Demo slug can only contain lowercase letters, numbers, and hyphens",
      );
      return;
    }
    if (
      isPlatformAdmin &&
      agentForm.is_demo &&
      agentForm.demo_public_result_url.trim()
    ) {
      try {
        const resultUrl = new URL(agentForm.demo_public_result_url.trim());
        if (
          resultUrl.protocol !== "https:" ||
          !resultUrl.hostname ||
          resultUrl.username ||
          resultUrl.password
        ) {
          throw new Error("invalid scheme");
        }
      } catch {
        toast.error("Public result URL must be a valid HTTPS URL");
        return;
      }
    }
    if (
      isPlatformAdmin &&
      (!Number.isInteger(agentForm.demo_calls_remaining) ||
        agentForm.demo_calls_remaining < -1)
    ) {
      toast.error("Demo calls remaining must be -1 or a whole number of calls");
      return;
    }
    if (
      isPlatformAdmin &&
      (!Number.isInteger(agentForm.demo_max_call_duration_minutes) ||
        (agentForm.demo_max_call_duration_minutes !== -1 &&
          agentForm.demo_max_call_duration_minutes <= 0))
    ) {
      toast.error("Demo call duration must be -1 or greater than zero minutes");
      return;
    }

    setSaving(true);
    try {
      const payload: Record<string, unknown> = {
        ...agentForm,
        instructions_markdown: buildAgentInstructionsMarkdown({
          role: agentForm.persona,
          tone: agentForm.tone,
          markdown: agentForm.instructions_markdown,
        }),
      };
      if (!isPlatformAdmin) {
        delete payload.is_demo;
        delete payload.demo_slug;
        delete payload.public_description;
        delete payload.demo_public_result_url;
        delete payload.demo_calls_remaining;
        delete payload.demo_max_call_duration_minutes;
      } else if (!payload.is_demo) {
        payload.demo_slug = null;
      }
      delete payload.demo_max_call_duration_minutes;
      if (isPlatformAdmin) {
        payload.demo_max_call_duration_seconds =
          agentForm.demo_max_call_duration_minutes === -1
            ? -1
            : agentForm.demo_max_call_duration_minutes * 60;
      }
      await updateAgentMutation.mutateAsync({
        agentId,
        data: payload as unknown as VoiceAgentUpdate,
      });
    } catch (error) {
      console.error("Failed to save agent:", error);
    } finally {
      setSaving(false);
    }
  }, [agentForm, agentId, isPlatformAdmin, updateAgentMutation]);

  const handleDeleteSuccess = useCallback(
    async (deletedAgentId: string) => {
      try {
        await deleteAgentMutation.mutateAsync(deletedAgentId);
        setDeleteDialogOpen(false);
        router.push("/agents");
      } catch (error) {
        console.error("Failed to delete agent:", error);
        throw error;
      }
    },
    [deleteAgentMutation, router],
  );

  if (agentError) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-destructive">Failed to load agent</div>
      </div>
    );
  }

  if (agentLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 text-muted-foreground animate-spin" />
        <span className="ml-3 text-muted-foreground">Loading agent...</span>
      </div>
    );
  }

  if (!agent) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-destructive">Agent not found</div>
      </div>
    );
  }

  const canEdit =
    isPlatformAdmin ||
    Boolean(user?.hasRole("org_admin", agent.organization_id));

  const contextValue: AgentDetailPageRenderContext = {
    agent,
    organization,
    agentForm,
    setAgentForm,
    canEdit,
    isPlatformAdmin,
    assignedPhoneNumber,
    setAssignedPhoneNumber,
  };

  return (
    <AgentDetailPageContext.Provider value={contextValue}>
      <div className="space-y-6" data-tour="agent-detail-page">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex min-w-0 items-center gap-3 sm:gap-4">
            <Button variant="ghost" size="icon" onClick={() => router.back()}>
              <ArrowLeft className="h-5 w-5" />
            </Button>
            <div className="shrink-0 rounded-lg bg-primary/10 p-3">
              <Bot className="h-6 w-6 text-primary" />
            </div>
            <div className="min-w-0">
              <h1 className="truncate text-xl font-bold sm:text-2xl">{agent.name}</h1>
              <p className="text-sm text-muted-foreground">
                {organization?.name || "Unknown Organization"}
              </p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2 sm:justify-end">
            {canEdit && (
              <>
                <Button
                  variant="outline"
                  onClick={() => setTestCallOpen(true)}
                  data-tour="agent-detail-test"
                  disabled={!voiceProfileReady && !voiceProfileReadinessLoading}
                  title={
                    !voiceProfileReady && !voiceProfileReadinessLoading
                      ? "Configure the voice profile before testing calls"
                      : undefined
                  }
                >
                  <Phone className="h-4 w-4 mr-2" />
                  Test Agent
                </Button>
                {agent.is_active && <EmbedButtonConfig agentId={agentId} />}
              </>
            )}
            {canEdit && (
              <DeleteButton onClick={() => setDeleteDialogOpen(true)}>
                Delete Agent
              </DeleteButton>
            )}
          </div>
        </div>

        {!voiceProfileReady && !voiceProfileReadinessLoading && (
          <PresetSetupCallout
            credentialsSelfService={credentialsSelfService}
            organizationId={agent.organization_id}
          />
        )}

        <AnimatedTabs
          value={activeTab}
          onValueChange={handleTabChange}
          className="space-y-6"
        >
          <TabsList className="w-full justify-start overflow-x-auto" data-tour="agent-detail-tabs">
            <TabsTrigger className="shrink-0 px-3 sm:px-6" value="persona">Persona</TabsTrigger>
            <TabsTrigger className="shrink-0 px-3 sm:px-6" value="skills">Skills</TabsTrigger>
            <TabsTrigger className="shrink-0 px-3 sm:px-6" value="tools">Tools</TabsTrigger>
            <TabsTrigger className="shrink-0 px-3 sm:px-6" value="settings">Settings</TabsTrigger>
            {recordingsTabVisible && (
              <TabsTrigger className="shrink-0 px-3 sm:px-6" value="recordings">Call History</TabsTrigger>
            )}
          </TabsList>

          <TabsContent value={activeTab}>
            {activeTab === "recordings" && recordingsLoading ? (
              <div className="flex items-center justify-center h-64">
                <Loader2 className="h-6 w-6 text-muted-foreground animate-spin" />
                <span className="ml-3 text-muted-foreground">
                  Loading call history...
                </span>
              </div>
            ) : (
              children
            )}
          </TabsContent>
        </AnimatedTabs>

        <AgentDetailSaveBar
          canEdit={canEdit}
          saving={saving || updateAgentMutation.isPending}
          onSave={handleSaveAgent}
        />

        {agent && testCallOpen && (
          <TestCallModal
            open={testCallOpen}
            onOpenChange={setTestCallOpen}
            agentId={agent.id}
            agentName={agent.name}
          />
        )}

        {agent && deleteDialogOpen && (
          <AgentDeleteDialog
            open={deleteDialogOpen}
            onOpenChange={setDeleteDialogOpen}
            agent={agent}
            onSuccess={handleDeleteSuccess}
          />
        )}
      </div>
    </AgentDetailPageContext.Provider>
  );
}
