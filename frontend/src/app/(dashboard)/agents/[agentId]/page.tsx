"use client";

import React, { useCallback, useEffect } from "react";
import { toast } from "sonner";
import { useAuth } from "@/contexts/auth-context";
import { useUserPermissions } from "@/hooks/use-user-permissions";
import { useRealtime } from "@/hooks/use-realtime";
import { useCallLogs } from "@/hooks/use-call-logs";
import {
  useAgent,
  usePlatformTools,
  useAgentTools,
  useUpdateAgent,
  useToggleFunction,
  useUpdateAgentTool,
  useStartOAuth,
  useLogoutAgentTool,
  useDeleteAgent,
  useDeleteAgentTool,
  useConfigureAgentTool,
  useAgentSystemPrompt,
} from "@/hooks/use-agent-queries";
import { organizationService } from "@/services/organization-service";
import { agentService } from "@/services/agent-service";
import { billingService } from "@/services/billing-service";
import type { PlatformTool, AgentTool } from "@/types/agent";
import type { OrgEntitlements } from "@/types/billing";
import type { Organization } from "@/types/organization";
import { AuthStatus } from "@/types/agent";
import { AgentDeleteDialog } from "@/components/agents/agent-delete-dialog";
import { TestCallModal } from "@/components/agents/test-call-modal";
import { EmbedButtonConfig } from "@/components/agents/embed-button-config";
import { PresetPicker, useSelectedPresetReadiness } from "@/components/agents/preset-picker";
import { PresetSetupCallout } from "@/components/agents/preset-setup-callout";
import { AgentPhoneNumberSelector } from "@/components/agents/agent-phone-number-selector";
import { AgentInstructionsHelpText } from "@/components/agents/agent-instructions-help-text";
import { AgentCallRecordings } from "@/components/calls/agent-call-recordings";
import { ToolDisconnectDialog } from "@/components/tools/tool-disconnect-dialog";
import { DeleteButton } from "@/components/ui/delete-button";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  ToolCard,
  ToolFilters,
  ToolConfigDrawer,
  ToolApiKeySetupDialog,
  ToolFilterType,
} from "@/components/tools";
import { buildAgentToolsDisplay } from "@/components/tools/tools-display";
import {
  AnimatedTabs,
  TabsList,
  TabsTrigger,
  TabsContent,
} from "@/components/ui/tabs";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import { Bot, Settings, Save, ArrowLeft, Loader2, Wrench, Info, Eye, EyeOff, Phone, ExternalLink, FileText, ChevronDown, Zap, FolderOpen } from "lucide-react";
import { MarkdownRenderer } from "@/components/markdown";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { voiceTemplateService } from "@/services/voice-template-service";
import type { VoiceTemplate } from "@/types/voice-template";
import { skillService } from "@/services/skill-service";
import type { OrganizationSkill } from "@/types/skill";
import type { PhoneNumberWithAgent } from "@/types/phone-number";
import {
  normalizeAgentDetailTab,
  shouldShowAgentRecordingsTab,
  type AgentDetailTab,
} from "@/components/agents/agent-detail-tabs";
import {
  buildAgentInstructionsMarkdown,
  buildMarkdownFromTemplate,
  DEFAULT_AGENT_INSTRUCTIONS_PLACEHOLDER,
} from "@/lib/agent-instructions";
import { useRouter, useParams, useSearchParams } from "next/navigation";
import Link from "next/link";

const AGENT_REALTIME_TABLES = ["agent_tools", "voice_agents"];

/**
 * Determines whether an MCP tool must collect an organization API key before
 * it can be attached to an agent. A literal platform credential makes the
 * key optional; an organization key, when supplied, remains the runtime
 * credential without mutating that platform fallback.
 */
function requiresOrganizationApiKeyBeforeConnect(
  tool: PlatformTool,
  isConnected: boolean,
): boolean {
  return (
    !isConnected &&
    tool.tool_source === "mcp" &&
    tool.auth_type === "api_key" &&
    tool.requires_auth !== false
  );
}

export default function AgentDetailPage() {
  const { user } = useAuth();
  const { isPlatformAdmin } = useUserPermissions();
  const router = useRouter();
  const params = useParams();
  const searchParams = useSearchParams();
  const agentId = params.agentId as string;

  const [organization, setOrganization] = React.useState<Organization | null>(
    null,
  );
  const [assignedPhoneNumber, setAssignedPhoneNumber] =
    React.useState<PhoneNumberWithAgent | null>(null);
  const [saving, setSaving] = React.useState(false);
  const [localAgentTools, setLocalAgentTools] = React.useState<AgentTool[]>([]);
  const [deleteDialogOpen, setDeleteDialogOpen] = React.useState(false);
  const [disconnectDialogOpen, setDisconnectDialogOpen] = React.useState(false);
  const [disconnectingToolId, setDisconnectingToolId] = React.useState<
    string | null
  >(null);
  const [activeTab, setActiveTab] = React.useState<AgentDetailTab>("persona");
  const [pendingToolToOpen, setPendingToolToOpen] =
    React.useState<PlatformTool | null>(null);
  const [pendingApiKeyTool, setPendingApiKeyTool] =
    React.useState<PlatformTool | null>(null);
  const [connectingToolId, setConnectingToolId] = React.useState<string | null>(
    null,
  );
  const [toolDrawerOpen, setToolDrawerOpen] = React.useState(false);
  const [showSystemPrompt, setShowSystemPrompt] = React.useState(false);
  const [testCallOpen, setTestCallOpen] = React.useState(false);
  const [voiceTemplates, setVoiceTemplates] = React.useState<VoiceTemplate[]>([]);
  const [pendingTemplate, setPendingTemplate] = React.useState<VoiceTemplate | null>(null);
  const [orgSkills, setOrgSkills] = React.useState<OrganizationSkill[]>([]);
  const [agentSkillIds, setAgentSkillIds] = React.useState<Set<string>>(new Set());
  const [skillsLoading, setSkillsLoading] = React.useState(false);
  const [skillToggling, setSkillToggling] = React.useState<string | null>(null);
  const [viewingSkill, setViewingSkill] = React.useState<OrganizationSkill | null>(null);
  const [viewingSkillFiles, setViewingSkillFiles] = React.useState<import("@/types/skill").SkillFileSummary[]>([]);
  const [viewingFile, setViewingFile] = React.useState<{ filePath: string; content: string } | null>(null);
  const [loadingViewFile, setLoadingViewFile] = React.useState(false);

  // Enable real-time updates for this agent's tools
  useRealtime(agentId, {
    tables: AGENT_REALTIME_TABLES, // Database table is voice_agents, not agents
  });

  const [selectedTool, setSelectedTool] = React.useState<PlatformTool | null>(
    null,
  );
  const [toolSearchQuery, setToolSearchQuery] = React.useState("");
  const [toolFilterType, setToolFilterType] =
    React.useState<ToolFilterType>("all");

  // Agent form state
  const [agentForm, setAgentForm] = React.useState<{
    name: string;
    persona: string;
    tone: string;
    is_active: boolean;
    is_published_on_public_page: boolean;
    call_recording_enabled: boolean;
    use_platform_credits: boolean;
    instructions_markdown: string;
    preset_id: string | null;
  }>({
    name: "",
    persona: "",
    tone: "",
    is_active: true,
    is_published_on_public_page: false,
    call_recording_enabled: false,
    use_platform_credits: false,
    instructions_markdown: "",
    preset_id: null,
  });

  // Fetch data using React Query
  const {
    data: agent,
    isLoading: agentLoading,
    error: agentError,
  } = useAgent(agentId);
  const { data: platformTools = [], isLoading: toolsLoading } =
    usePlatformTools(true, { enabled: activeTab === "tools" });
  const { data: agentTools = [], refetch: refetchAgentTools } =
    useAgentTools(agentId, activeTab === "tools");

  const canViewRecordings =
    isPlatformAdmin ||
    Boolean(agent && user?.hasRole("org_admin", agent.organization_id));
  const { data: agentRecordingSummary } = useCallLogs(
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

  // Org plan entitlements drive the premium-tool gate (blocked connect when
  // the 'premium_tools' feature is off). Fetched once the agent resolves its
  // organization; the API enforces the same gate.
  const [orgEntitlements, setOrgEntitlements] =
    React.useState<OrgEntitlements | null>(null);
  React.useEffect(() => {
    if (!agent?.organization_id || activeTab !== "tools") return;
    let cancelled = false;
    billingService
      .getOrganizationEntitlements(agent.organization_id)
      .then((data) => {
        if (!cancelled) setOrgEntitlements(data);
      })
      .catch((error) => {
        console.error("Failed to load organization entitlements:", error);
      });
    return () => {
      cancelled = true;
    };
  }, [activeTab, agent?.organization_id]);

  const premiumToolsBlocked = !orgEntitlements?.features["premium_tools"]
    ?.effective_value;

  // Fetch system prompt preview
  const {
    data: systemPromptPreview,
    isLoading: systemPromptLoading,
  } = useAgentSystemPrompt(agentId, showSystemPrompt);

  // Mutations
  const updateAgentMutation = useUpdateAgent();
  const deleteAgentMutation = useDeleteAgent();
  const toggleFunctionMutation = useToggleFunction();
  const updateAgentToolMutation = useUpdateAgentTool();
  const startOAuthMutation = useStartOAuth();
  const logoutAgentToolMutation = useLogoutAgentTool();
  const deleteAgentToolMutation = useDeleteAgentTool();
  const configureAgentToolMutation = useConfigureAgentTool();

  const {
    isReady: voiceProfileReady,
    isLoading: voiceProfileReadinessLoading,
    credentialsSelfService,
  } = useSelectedPresetReadiness(
    agent?.organization_id,
    agentForm.preset_id,
    agentForm.use_platform_credits,
  );

  // Load organization when agent data is available
  React.useEffect(() => {
    if (agent?.organization_id) {
      organizationService
        .getOrganizationById(agent.organization_id)
        .then(setOrganization)
        .catch((error) => {
          console.error("Failed to load organization:", error);
        });
    }
  }, [agent?.organization_id]);

  // Load use case templates for the "Insert template" dropdown
  React.useEffect(() => {
    voiceTemplateService
      .listTemplates()
      .then(setVoiceTemplates)
      .catch(() => {});
  }, []);

  // Load org skills and agent skill assignments
  React.useEffect(() => {
    if (!agent?.organization_id || activeTab !== "skills") return;
    setSkillsLoading(true);
    Promise.all([
      skillService.getOrganizationSkills(agent.organization_id),
      skillService.getAgentSkills(agentId),
    ])
      .then(([skills, agentSkills]) => {
        // Show all active skills; hidden ones will be shown if assigned
        setOrgSkills(skills.filter((s) => s.is_active));
        setAgentSkillIds(new Set(agentSkills.map((as) => as.skill_id)));
      })
      .catch((err) => {
        console.error("Failed to load skills:", err);
      })
      .finally(() => setSkillsLoading(false));
  }, [activeTab, agent?.organization_id, agentId]);

  // Fetch skill files when viewing a skill in the drawer
  React.useEffect(() => {
    if (viewingSkill && agent?.organization_id) {
      setViewingFile(null);
      skillService.getSkillFiles(agent.organization_id, viewingSkill.id)
        .then(setViewingSkillFiles)
        .catch(() => setViewingSkillFiles([]));
    } else {
      setViewingSkillFiles([]);
    }
  }, [viewingSkill, agent?.organization_id]);

  const handleSkillToggle = useCallback(async (skillId: string, assign: boolean) => {
    setSkillToggling(skillId);
    try {
      if (assign) {
        await skillService.assignSkill(agentId, skillId);
        setAgentSkillIds((prev) => new Set([...prev, skillId]));
      } else {
        await skillService.unassignSkill(agentId, skillId);
        setAgentSkillIds((prev) => {
          const next = new Set(prev);
          next.delete(skillId);
          return next;
        });
      }
    } catch {
      toast.error(`Failed to ${assign ? "assign" : "unassign"} skill`);
    } finally {
      setSkillToggling(null);
    }
  }, [agentId]);

  // Update form when agent data changes. Older agents may only have the
  // structured prompt fields, so hydrate Markdown from the existing API
  // endpoint when no canonical instructions have been saved yet.
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

  // Sync local agent tools state with query data
  React.useEffect(() => {
    if (agentTools.length > 0) {
      setLocalAgentTools(agentTools);
    }
  }, [agentTools]);

  // Open drawer when a pending tool has been connected
  React.useEffect(() => {
    if (pendingToolToOpen && localAgentTools.length > 0) {
      const newAgentTool = localAgentTools.find(
        (at) => at.tool_id === pendingToolToOpen.id,
      );
      if (newAgentTool) {
        setSelectedTool(pendingToolToOpen);
        setToolDrawerOpen(true);
        setPendingToolToOpen(null);
        setConnectingToolId(null);
      }
    }
  }, [pendingToolToOpen, localAgentTools]);

  // Sync tab state with URL
  useEffect(() => {
    const requestedTab = normalizeAgentDetailTab(searchParams.get("tab"));
    setActiveTab(
      requestedTab === "recordings" && !recordingsTabVisible
        ? "persona"
        : requestedTab,
    );
  }, [recordingsTabVisible, searchParams]);

  const handleTabChange = useCallback(
    (value: string) => {
      const tab = normalizeAgentDetailTab(value);
      setActiveTab(tab);
      router.push(`/agents/${agentId}?tab=${tab}`, { scroll: false });
    },
    [router, agentId],
  );

  const handleSaveAgent = useCallback(async () => {
    if (!agentId) return;

    setSaving(true);
    try {
      await updateAgentMutation.mutateAsync({
        agentId,
        data: {
          ...agentForm,
          instructions_markdown: buildAgentInstructionsMarkdown({
            role: agentForm.persona,
            tone: agentForm.tone,
            markdown: agentForm.instructions_markdown,
          }),
        },
      });
    } catch (error) {
      console.error("Failed to save agent:", error);
    } finally {
      setSaving(false);
    }
  }, [agentId, agentForm, updateAgentMutation]);

  const handleDeleteAgent = async () => {
    setDeleteDialogOpen(true);
  };

  const handleDeleteSuccess = useCallback(
    async (agentId: string) => {
      try {
        await deleteAgentMutation.mutateAsync(agentId);
        setDeleteDialogOpen(false);
        router.push("/agents");
      } catch (error) {
        console.error("Failed to delete agent:", error);
        throw error;
      }
    },
    [deleteAgentMutation, router],
  );

  const handleToggleFunction = useCallback(
    async (toolId: string, functionName: string, isChecked: boolean) => {
      const existingAgentTool = localAgentTools.find(
        (at) => at.tool_id === toolId,
      );
      if (!existingAgentTool) return;

      const currentUnselected = existingAgentTool.unselected_functions || [];
      let newUnselected: string[];

      if (isChecked) {
        newUnselected = currentUnselected.filter((fn) => fn !== functionName);
      } else {
        newUnselected = currentUnselected.includes(functionName)
          ? currentUnselected
          : [...currentUnselected, functionName];
      }

      await toggleFunctionMutation.mutateAsync({
        agentToolId: existingAgentTool.id,
        unselectedFunctions: newUnselected,
      });
    },
    [localAgentTools, toggleFunctionMutation],
  );

  const handleSaveToolConfig = useCallback(
    async (agentToolId: string, config: Record<string, unknown>) => {
      try {
        await updateAgentToolMutation.mutateAsync({
          agentToolId,
          data: { config },
        });
      } catch (error) {
        console.error("Failed to save tool config:", error);
      }
    },
    [updateAgentToolMutation],
  );

  const handleOAuth = useCallback(
    async (toolName: string) => {
      try {
        await startOAuthMutation.mutateAsync({ toolName, agentId });
      } catch (error) {
        console.error("OAuth failed:", error);
      }
    },
    [agentId, startOAuthMutation],
  );

  const handleLogout = useCallback(
    async (agentToolId: string) => {
      try {
        await logoutAgentToolMutation.mutateAsync(agentToolId);
      } catch (error) {
        console.error("Failed to log out:", error);
      }
    },
    [logoutAgentToolMutation],
  );

  const handleSetApiKey = useCallback(
    async (agentToolId: string, apiKey: string) => {
      try {
        await agentService.setApiKey(agentToolId, apiKey);
        toast.success("API Key Saved", {
          description: "Your API key has been configured successfully.",
        });
      } catch (error) {
        console.error("Failed to set API key:", error);
        toast.error("Error", {
          description: "Failed to save API key. Please try again.",
        });
      }
    },
    [],
  );

  const handleDisconnect = useCallback(
    async (agentToolId: string) => {
      try {
        await deleteAgentToolMutation.mutateAsync(agentToolId);
        setLocalAgentTools((prev) =>
          prev.filter((tool) => tool.id !== agentToolId),
        );
      } catch (error) {
        console.error("Failed to disconnect:", error);
        throw error;
      }
    },
    [deleteAgentToolMutation],
  );

  const handleCloseDisconnectDialog = useCallback(() => {
    setDisconnectDialogOpen(false);
    setDisconnectingToolId(null);
    setToolDrawerOpen(false);
  }, []);

  const handleToolCardClick = useCallback(
    async (tool: PlatformTool) => {
      const existingAgentTool = localAgentTools.find(
        (at) => at.tool_id === tool.id,
      );

      if (!existingAgentTool) {
        if (requiresOrganizationApiKeyBeforeConnect(tool, false)) {
          setPendingApiKeyTool(tool);
          return;
        }

        // Premium tools are gated on the plan's 'premium_tools' feature: keep
        // the card visible with a badge but block the attach action (the API
        // enforces the same gate server-side). Already-connected premium tools
        // keep working and remain editable.
        if (tool.is_premium && premiumToolsBlocked) {
          toast.error("Premium Tool", {
            description:
              "Premium tools are not included in your current plan. Upgrade your plan to connect this tool.",
          });
          return;
        }
        try {
          setConnectingToolId(tool.id);
          setPendingToolToOpen(tool);
          await configureAgentToolMutation.mutateAsync({
            agent_id: agentId,
            tool_id: tool.id,
            is_enabled: true,
          });
        } catch (error) {
          console.error("Failed to configure tool:", error);
          setPendingToolToOpen(null);
          setConnectingToolId(null);
        }
      } else {
        setSelectedTool(tool);
        setToolDrawerOpen(true);
      }
    },
    [agentId, localAgentTools, configureAgentToolMutation, premiumToolsBlocked],
  );

  const handleRequiredApiKeyConnect = useCallback(
    async (apiKey: string) => {
      if (!pendingApiKeyTool) return;

      const tool = pendingApiKeyTool;
      try {
        setConnectingToolId(tool.id);
        setPendingToolToOpen(tool);
        await configureAgentToolMutation.mutateAsync({
          agent_id: agentId,
          tool_id: tool.id,
          is_enabled: true,
          sensitive_config: { api_key: apiKey },
        });
        setPendingApiKeyTool(null);
      } catch (error) {
        setPendingToolToOpen(null);
        setConnectingToolId(null);
        console.error("Failed to connect MCP tool with API key:", error);
        throw error;
      }
    },
    [agentId, configureAgentToolMutation, pendingApiKeyTool],
  );

  const handleCloseToolDrawer = useCallback(() => {
    setToolDrawerOpen(false);
    setSelectedTool(null);
    refetchAgentTools();
  }, [refetchAgentTools]);

  // Connected tools whose platform tool is unpublished (RFC §6.6). The worker
  // loads an agent's tools by joining `agent_tools` -> `platform_tools` without
  // filtering on `is_published`, so the agent keeps these at runtime even after
  // the platform admin unpublishes them. The catalog (`usePlatformTools`) only
  // returns published rows, so without this merge the card would vanish from the
  // Tools tab even though the agent still uses it. Here we surface those tools
  // inline in the grid, flagged `isUnpublished` so the card renders an amber
  // "Unpublished" pill + note. Unpublished AND not mapped -> not in
  // `localAgentTools` -> never rendered (unchanged behavior). Logic lives in
  // `buildAgentToolsDisplay` so it's unit-tested in isolation (the full page is
  // too heavy to mount for a pure merge).
  const { allTools, unpublishedConnectedIds } = React.useMemo(
    () => buildAgentToolsDisplay(platformTools, localAgentTools),
    [platformTools, localAgentTools],
  );

  const getFilteredTools = useCallback(() => {
    let filtered = allTools;

    if (toolSearchQuery) {
      const query = toolSearchQuery.toLowerCase();
      filtered = filtered.filter(
        (tool) =>
          tool.name.toLowerCase().includes(query) ||
          tool.description?.toLowerCase().includes(query),
      );
    }

    if (toolFilterType === "connected") {
      filtered = filtered.filter(
        (tool) =>
          localAgentTools.find((at) => at.tool_id === tool.id) !== undefined,
      );
    } else if (toolFilterType === "not_connected") {
      filtered = filtered.filter(
        (tool) => !localAgentTools.find((at) => at.tool_id === tool.id),
      );
    }

    return filtered;
  }, [allTools, toolSearchQuery, toolFilterType, localAgentTools]);

  const filteredTools = getFilteredTools();

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
    (agent && user?.hasRole("org_admin", agent.organization_id)) ||
    false;

  return (
    <div className="space-y-6" data-tour="agent-detail-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Button variant="ghost" size="icon" onClick={() => router.back()}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div className="bg-primary/10 p-3 rounded-lg">
            <Bot className="h-6 w-6 text-primary" />
          </div>
          <div>
            <h1 className="text-2xl font-bold">{agent.name}</h1>
            <p className="text-sm text-muted-foreground">
              {organization?.name || "Unknown Organization"}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
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
            <DeleteButton onClick={handleDeleteAgent}>Delete Agent</DeleteButton>
          )}
        </div>
      </div>

      {!voiceProfileReady && !voiceProfileReadinessLoading && agent && (
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
        <TabsList className="w-full" data-tour="agent-detail-tabs">
          <TabsTrigger value="persona">Persona</TabsTrigger>
          <TabsTrigger value="skills">Skills</TabsTrigger>
          <TabsTrigger value="tools">Tools</TabsTrigger>
          <TabsTrigger value="settings">Settings</TabsTrigger>
          {recordingsTabVisible && (
            <TabsTrigger value="recordings">Call History</TabsTrigger>
          )}
        </TabsList>

        {/* Persona Tab */}
        <TabsContent value="persona">
          <Card data-tour="agent-detail-persona">
            <CardHeader className="p-5 pb-3">
              <CardTitle className="flex items-center space-x-2 text-lg">
                <Bot className="h-5 w-5" />
                <span>Agent Persona</span>
              </CardTitle>
              <CardDescription>
                Define how your agent represents your business and communicates with callers
              </CardDescription>
            </CardHeader>
            <CardContent className="p-5 pt-0 space-y-4">
              <div className="bg-blue-50 border border-blue-200 rounded-md p-3 flex items-start gap-2">
                <Info className="h-4 w-4 text-blue-600 mt-0.5 flex-shrink-0" />
                <p className="text-sm text-blue-800">
                  The information you provide here helps the AI agent represent your business accurately when speaking with callers.
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="name">Name</Label>
                <Input
                  id="name"
                  value={agentForm.name}
                  onChange={(e) =>
                    setAgentForm({ ...agentForm, name: e.target.value })
                  }
                  disabled={!canEdit}
                />
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="agent-role">Agent Role</Label>
                  <Input
                    id="agent-role"
                    value={agentForm.persona}
                    onChange={(e) =>
                      setAgentForm({ ...agentForm, persona: e.target.value })
                    }
                    placeholder="Front Desk Coordinator"
                    disabled={!canEdit}
                  />
                  <p className="text-xs text-muted-foreground">
                    The character or job title this agent represents.
                  </p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="communication-style">Communication Style</Label>
                  <Input
                    id="communication-style"
                    value={agentForm.tone}
                    onChange={(e) =>
                      setAgentForm({ ...agentForm, tone: e.target.value })
                    }
                    placeholder="Warm, professional, and reassuring"
                    disabled={!canEdit}
                  />
                  <p className="text-xs text-muted-foreground">
                    How the agent should communicate with callers.
                  </p>
                </div>
              </div>

              {/* Additional Instructions (Markdown) */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <Label htmlFor="instructions_markdown" className="text-sm font-medium">
                      Additional Instructions
                    </Label>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      <AgentInstructionsHelpText />
                    </p>
                  </div>
                  {canEdit && voiceTemplates.length > 0 && (
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="outline" size="sm">
                          <FileText className="w-3.5 h-3.5 mr-1.5" />
                          Insert template
                          <ChevronDown className="w-3.5 h-3.5 ml-1" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end" className="w-64">
                        {voiceTemplates.map((template) => (
                          <DropdownMenuItem
                            key={template.id}
                            onClick={() => {
                              if (agentForm.instructions_markdown?.trim()) {
                                setPendingTemplate(template);
                                return;
                              }
                              const markdown = buildMarkdownFromTemplate(template);
                              setAgentForm({
                                ...agentForm,
                                persona: template.persona || agentForm.persona,
                                tone: template.tone || agentForm.tone,
                                instructions_markdown: markdown,
                              });
                              toast.success(`"${template.name}" template inserted`);
                            }}
                          >
                            <div>
                              <div className="font-medium text-sm">{template.name}</div>
                              <div className="text-xs text-muted-foreground">{template.industry}</div>
                            </div>
                          </DropdownMenuItem>
                        ))}
                      </DropdownMenuContent>
                    </DropdownMenu>
                  )}
                </div>
                <Textarea
                  id="instructions_markdown"
                  value={agentForm.instructions_markdown}
                  onChange={(e) =>
                    setAgentForm({
                      ...agentForm,
                      instructions_markdown: e.target.value,
                    })
                  }
                  placeholder={DEFAULT_AGENT_INSTRUCTIONS_PLACEHOLDER}
                  className="min-h-[400px] font-mono text-sm"
                  disabled={!canEdit}
                />
              </div>

              {/* System Prompt Preview Section */}
              <div className="border rounded-lg overflow-hidden">
                <button
                  type="button"
                  onClick={() => setShowSystemPrompt(!showSystemPrompt)}
                  className="w-full px-4 py-3 bg-slate-50 hover:bg-slate-100 transition-colors flex items-center justify-between text-left"
                >
                  <div className="flex items-center gap-2">
                    {showSystemPrompt ? (
                      <EyeOff className="h-4 w-4 text-slate-600" />
                    ) : (
                      <Eye className="h-4 w-4 text-slate-600" />
                    )}
                    <span className="font-medium text-sm">Preview System Prompt</span>
                  </div>
                  <span className="text-xs text-muted-foreground">
                    {showSystemPrompt ? "Click to hide" : "Click to view"}
                  </span>
                </button>

                {showSystemPrompt && (
                  <div className="p-4 bg-slate-50 border-t">
                    <p className="text-sm text-muted-foreground mb-3">
                      This is the final system prompt the AI receives — your markdown instructions plus system guardrails and tool guidelines.
                    </p>
                    {systemPromptLoading ? (
                      <div className="flex items-center justify-center py-8">
                        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                        <span className="ml-2 text-sm text-muted-foreground">Generating preview...</span>
                      </div>
                    ) : systemPromptPreview ? (
                      <div className="bg-white border rounded-md p-4 overflow-x-auto prose prose-sm prose-slate max-w-none">
                        <MarkdownRenderer content={systemPromptPreview} />
                      </div>
                    ) : (
                      <div className="text-center py-8 text-muted-foreground text-sm">
                        Unable to generate preview. Save your instructions first, then check the preview.
                      </div>
                    )}
                  </div>
                )}
              </div>

            </CardContent>
          </Card>
        </TabsContent>

        {/* Settings Tab */}
        <TabsContent value="settings">
          <div className="space-y-6">
            <Card>
              <CardHeader className="p-5 pb-3">
                <CardTitle className="flex items-center space-x-2 text-lg">
                  <Settings className="h-5 w-5" />
                  <span>Agent Settings</span>
                </CardTitle>
                <CardDescription>
                  Control how this agent is used and where it can respond
                </CardDescription>
              </CardHeader>
              <CardContent className="p-5 pt-0 space-y-6">
                <div className="space-y-2">
                  <AgentPhoneNumberSelector
                    agentId={agentId}
                    organizationId={agent.organization_id}
                    canEdit={canEdit}
                    onAssignmentChange={setAssignedPhoneNumber}
                  />
                </div>

                <div className="border-t pt-5 space-y-6">
                  <div className="space-y-2">
                    <div className="flex items-center space-x-2">
                      <Switch
                        id="active"
                        checked={agentForm.is_active}
                        onCheckedChange={(checked) => {
                          if (checked && !assignedPhoneNumber) {
                            toast.warning(
                              "A phone number is required to activate this agent. Please assign a phone number first.",
                            );
                            return;
                          }
                          // Deactivating also unpublishes — inactive agents must not
                          // remain listed on the public organization page.
                          setAgentForm({
                            ...agentForm,
                            is_active: checked === true,
                            ...(checked
                              ? {}
                              : { is_published_on_public_page: false }),
                          });
                        }}
                        disabled={!canEdit}
                      />
                      <Label
                        htmlFor="active"
                        className="text-sm font-normal cursor-pointer"
                      >
                        Agent is active and ready to handle calls
                      </Label>
                    </div>
                    {!assignedPhoneNumber && (
                      <p className="text-xs text-amber-600 flex items-center gap-1">
                        <Info className="w-3 h-3" />
                        A phone number must be configured before the agent can be activated.
                      </p>
                    )}
                  </div>

                  <div className="space-y-2">
                    <div className="flex items-center space-x-2">
                      <Switch
                        id="public-page-publish"
                        checked={agentForm.is_published_on_public_page}
                        onCheckedChange={(checked) => {
                          if (checked && !agentForm.is_active) {
                            toast.warning(
                              "Only active agents can be published on the public organization page.",
                            );
                            return;
                          }
                          setAgentForm({
                            ...agentForm,
                            is_published_on_public_page: checked === true,
                          });
                        }}
                        disabled={!canEdit || !agentForm.is_active}
                      />
                      <Label
                        htmlFor="public-page-publish"
                        className="text-sm font-normal cursor-pointer"
                      >
                        Publish on public organization page
                      </Label>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      When enabled, visitors at your organization&apos;s public URL can start a voice call with this agent. Requires the agent to be active.
                    </p>
                  </div>

                  <div className="space-y-2">
                    <div className="flex items-center space-x-2">
                      <Switch
                        id="call-recording"
                        checked={agentForm.call_recording_enabled}
                        onCheckedChange={(checked) =>
                          setAgentForm({
                            ...agentForm,
                            call_recording_enabled: checked === true,
                          })
                        }
                        disabled={!canEdit}
                      />
                      <Label
                        htmlFor="call-recording"
                        className="text-sm font-normal cursor-pointer"
                      >
                        Record calls for this agent
                      </Label>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      When enabled, your team can review recordings of this agent&apos;s calls. Inform callers and follow applicable consent requirements.
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="p-5 pb-3">
                <CardTitle className="text-lg">Voice Profile</CardTitle>
                <CardDescription>
                  Choose how this agent sounds when speaking with callers
                </CardDescription>
              </CardHeader>
              <CardContent className="p-5 pt-0">
                <PresetPicker
                  organizationId={agent.organization_id}
                  usePlatformCredits={agentForm.use_platform_credits}
                  value={agentForm.preset_id}
                  onChange={(presetId) =>
                    setAgentForm({ ...agentForm, preset_id: presetId })
                  }
                  disabled={!canEdit}
                />
              </CardContent>
            </Card>

            {canEdit && (
              <div className="flex space-x-2">
                <Button
                  onClick={handleSaveAgent}
                  disabled={saving || updateAgentMutation.isPending}
                >
                  <Save className="h-4 w-4 mr-2" />
                  {saving || updateAgentMutation.isPending
                    ? "Saving..."
                    : "Save Changes"}
                </Button>
              </div>
            )}
          </div>
        </TabsContent>

        {recordingsTabVisible && (
          <TabsContent value="recordings">
            <AgentCallRecordings
              organizationId={agent.organization_id}
              agentId={agent.id}
              agentName={agent.name}
            />
          </TabsContent>
        )}

        {/* Skills Tab */}
        <TabsContent value="skills">
          <Card>
            <CardHeader className="p-5 pb-3">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center space-x-2 text-lg">
                    <Zap className="h-5 w-5" />
                    <span>Agent Skills</span>
                  </CardTitle>
                  <CardDescription>
                    Assign skills to give this agent domain-specific knowledge and procedures.
                    Skills are loaded on-demand during conversations.
                  </CardDescription>
                </div>
                {canEdit && agent?.organization_id && (
                  <Link
                    href={`/organization?org_id=${agent.organization_id}&tab=skills`}
                    className="inline-flex items-center gap-1 text-sm text-primary hover:text-primary/80 underline underline-offset-2"
                  >
                    <ExternalLink className="h-3.5 w-3.5" />
                    Manage Skills
                  </Link>
                )}
              </div>
            </CardHeader>
            <CardContent className="p-5 pt-2">
              {skillsLoading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-6 w-6 animate-spin" />
                  <span className="ml-2 text-sm text-muted-foreground">Loading skills...</span>
                </div>
              ) : orgSkills.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <Zap className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>No skills available for this organization.</p>
                  <p className="text-sm mt-1">Add skills from Organization Settings to get started.</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {orgSkills.map((skill) => {
                    const isAssigned = agentSkillIds.has(skill.id);
                    const isToggling = skillToggling === skill.id;
                    return (
                      <div
                        key={skill.id}
                        className={cn(
                          "flex items-center justify-between p-4 border rounded-lg transition-colors cursor-pointer",
                          isAssigned ? "bg-primary/5 border-primary/20" : "hover:bg-muted/50",
                        )}
                        onClick={() => setViewingSkill(skill)}
                      >
                        <div className="flex items-start gap-3 flex-1 min-w-0">
                          <div onClick={(e) => e.stopPropagation()}>
                            <Switch
                              checked={isAssigned}
                              onCheckedChange={(checked) =>
                                handleSkillToggle(skill.id, checked === true)
                              }
                              disabled={!canEdit || isToggling}
                            />
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <span className="font-medium text-sm">{skill.name}</span>
                              <Badge
                                variant={skill.source_skill_id ? "secondary" : "outline"}
                                className="text-xs"
                              >
                                {skill.source_skill_id ? "Platform" : "Custom"}
                              </Badge>
                              {!skill.is_visible && (
                                <Badge variant="outline" className="text-[11px] border-orange-200 text-orange-600 bg-orange-50">
                                  <EyeOff className="h-3 w-3 mr-0.5" /> Hidden
                                </Badge>
                              )}
                            </div>
                            {skill.description && (
                              <p className="text-xs text-muted-foreground mt-0.5 truncate">
                                {skill.description}
                              </p>
                            )}
                          </div>
                        </div>
                        <Eye className="h-4 w-4 text-muted-foreground" />
                      </div>
                    );
                  })}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Skill content viewer drawer with file tree */}
        <Sheet open={!!viewingSkill} onOpenChange={(open) => {
          if (!open) {
            setViewingSkill(null);
          }
        }}>
          <SheetContent className="flex flex-col w-full sm:max-w-2xl">
            <SheetHeader className="px-6 pt-6 pb-4 border-b">
              <SheetTitle className="flex items-center gap-2">
                {viewingSkill?.name}
                <Badge
                  variant={viewingSkill?.source_skill_id ? "secondary" : "outline"}
                  className="text-xs"
                >
                  {viewingSkill?.source_skill_id ? "Platform" : "Custom"}
                </Badge>
              </SheetTitle>
              {viewingSkill?.description && (
                <SheetDescription>{viewingSkill.description}</SheetDescription>
              )}
            </SheetHeader>

            {viewingSkill && !viewingSkill.is_visible && (
              <div className="px-6 py-2.5 border-b bg-orange-50 flex items-center justify-between gap-3">
                <div className="flex items-center gap-1.5 text-sm text-orange-700">
                  <EyeOff className="h-4 w-4" />
                  <span>This skill is hidden from your organization library.</span>
                </div>
                {canEdit && agent?.organization_id && (
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-7 text-xs"
                    onClick={async () => {
                      try {
                        await skillService.updateSkill(agent.organization_id, viewingSkill.id, {
                          is_visible: true,
                        });
                        toast.success("Skill is now visible in the library");
                        // Refresh org skills list
                        const skills = await skillService.getOrganizationSkills(agent.organization_id);
                        setOrgSkills(skills.filter((s) => s.is_active));
                      } catch {
                        toast.error("Failed to update visibility");
                      }
                    }}
                  >
                    <Eye className="h-3.5 w-3.5 mr-1" />
                    Show in Library
                  </Button>
                )}
              </div>
            )}

            {/* File tabs */}
            {viewingSkillFiles.length > 0 && (
              <div className="px-6 py-2 border-b flex flex-wrap gap-1 bg-muted/20">
                <button
                  className={cn(
                    "px-2.5 py-1 rounded text-xs flex items-center gap-1 transition-colors",
                    !viewingFile
                      ? "bg-primary/10 text-primary font-medium"
                      : "text-muted-foreground hover:bg-muted"
                  )}
                  onClick={() => setViewingFile(null)}
                >
                  <FileText className="h-3 w-3" />
                  SKILL.md
                </button>
                {(() => {
                  const folders: Record<string, typeof viewingSkillFiles> = {};
                  const rootFiles: typeof viewingSkillFiles = [];
                  viewingSkillFiles.forEach((f) => {
                    const parts = f.file_path.split("/");
                    if (parts.length > 1) {
                      const folder = parts[0];
                      if (!folders[folder]) folders[folder] = [];
                      folders[folder].push(f);
                    } else {
                      rootFiles.push(f);
                    }
                  });
                  return (
                    <>
                      {Object.entries(folders).map(([folder, files]) => (
                        <div key={folder} className="flex items-center gap-0.5">
                          <span className="text-[10px] text-muted-foreground ml-1">
                            <FolderOpen className="h-3 w-3 inline mr-0.5" />{folder}/
                          </span>
                          {files.map((f) => (
                            <button
                              key={f.id}
                              className={cn(
                                "px-2 py-1 rounded text-xs flex items-center gap-1 transition-colors",
                                viewingFile?.filePath === f.file_path
                                  ? "bg-primary/10 text-primary font-medium"
                                  : "text-muted-foreground hover:bg-muted"
                              )}
                              onClick={async () => {
                                if (!agent?.organization_id || !viewingSkill) return;
                                setLoadingViewFile(true);
                                try {
                                  const content = await skillService.getSkillFileContent(
                                    agent.organization_id, viewingSkill.slug, f.file_path
                                  );
                                  setViewingFile({ filePath: f.file_path, content });
                                } catch {
                                  toast.error("Failed to load file");
                                }
                                setLoadingViewFile(false);
                              }}
                            >
                              <FileText className="h-3 w-3" />
                              {f.file_path.split("/").pop()}
                            </button>
                          ))}
                        </div>
                      ))}
                      {rootFiles.map((f) => (
                        <button
                          key={f.id}
                          className={cn(
                            "px-2 py-1 rounded text-xs flex items-center gap-1 transition-colors",
                            viewingFile?.filePath === f.file_path
                              ? "bg-primary/10 text-primary font-medium"
                              : "text-muted-foreground hover:bg-muted"
                          )}
                          onClick={async () => {
                            if (!agent?.organization_id || !viewingSkill) return;
                            setLoadingViewFile(true);
                            try {
                              const content = await skillService.getSkillFileContent(
                                agent.organization_id, viewingSkill.slug, f.file_path
                              );
                              setViewingFile({ filePath: f.file_path, content });
                            } catch {
                              toast.error("Failed to load file");
                            }
                            setLoadingViewFile(false);
                          }}
                        >
                          <FileText className="h-3 w-3" />
                          {f.file_path}
                        </button>
                      ))}
                    </>
                  );
                })()}
              </div>
            )}

            {/* Content area */}
            {loadingViewFile ? (
              <div className="flex-1 flex items-center justify-center">
                <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
              </div>
            ) : viewingFile ? (
              <>
                <div className="px-6 py-1.5 border-b bg-muted/30 text-xs text-muted-foreground flex items-center gap-2">
                  <FileText className="h-3.5 w-3.5" />
                  <code>{viewingFile.filePath}</code>
                </div>
                {viewingFile.filePath.endsWith(".json") ? (
                  <div className="flex-1 overflow-y-auto p-5">
                    <pre className="text-xs font-mono bg-muted/50 rounded-lg p-4 overflow-x-auto whitespace-pre">
                      {(() => { try { return JSON.stringify(JSON.parse(viewingFile.content), null, 2); } catch { return viewingFile.content; } })()}
                    </pre>
                  </div>
                ) : viewingFile.filePath.match(/\.(py|js|ts|sh|bash|yaml|yml|toml)$/) ? (
                  <div className="flex-1 overflow-y-auto p-5">
                    <pre className="text-xs font-mono bg-muted/50 rounded-lg p-4 overflow-x-auto whitespace-pre">
                      {viewingFile.content}
                    </pre>
                  </div>
                ) : (
                  <div className="flex-1 overflow-y-auto px-6 py-5 prose prose-sm prose-slate max-w-none">
                    <MarkdownRenderer content={viewingFile.content} />
                  </div>
                )}
              </>
            ) : (
              <div className="flex-1 overflow-y-auto px-6 py-5 prose prose-sm prose-slate max-w-none">
                {viewingSkill && <MarkdownRenderer content={viewingSkill.content} />}
              </div>
            )}
          </SheetContent>
        </Sheet>

        {/* Tools Tab */}
        <TabsContent value="tools">
          <Card>
            <CardHeader className="p-5 pb-3">
              <div>
                <CardTitle className="flex items-center space-x-2 text-lg">
                  <Wrench className="h-5 w-5" />
                  <span>Tool Configuration</span>
                </CardTitle>
                <CardDescription>
                  Configure platform tools for {agent.name}
                </CardDescription>
              </div>
            </CardHeader>
            <CardContent className="p-5 pt-0">
              {toolsLoading ? (
                <div className="flex flex-col items-center justify-center py-12 space-y-4">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
                  <p className="text-sm text-muted-foreground">
                    Loading tools...
                  </p>
                </div>
              ) : allTools.length === 0 ? (
                <div className="text-center py-12 bg-muted/20 rounded-lg">
                  <Wrench className="h-8 w-8 text-muted-foreground mx-auto mb-2 opacity-50" />
                  <p className="text-muted-foreground">
                    No platform tools available
                  </p>
                </div>
              ) : (
                <div className="space-y-6">
                  {/* Tool Selection Guidance */}
                  <div className="bg-amber-50 border border-amber-200 rounded-md p-3 flex items-start gap-2">
                    <Info className="h-4 w-4 text-amber-600 mt-0.5 flex-shrink-0" />
                    <div className="text-sm text-amber-800 space-y-1">
                      <p className="font-medium">Best Practice: Keep Tool Selection Focused</p>
                      <p>
                        Only enable the tools your agent truly needs. Too many tools can confuse the AI and reduce response quality.
                        For each tool set you connect, selectively enable only the specific functions required for your use case.
                      </p>
                    </div>
                  </div>

                  <ToolFilters
                    searchQuery={toolSearchQuery}
                    onSearchChange={setToolSearchQuery}
                    filterType={toolFilterType}
                    onFilterChange={setToolFilterType}
                    totalCount={allTools.length}
                    filteredCount={filteredTools.length}
                  />

                  {filteredTools.length === 0 ? (
                    <div className="text-center py-12 bg-muted/20 rounded-lg">
                      <Wrench className="h-8 w-8 text-muted-foreground mx-auto mb-2 opacity-50" />
                      <p className="text-muted-foreground">
                        No tools match your search
                      </p>
                    </div>
                  ) : (
                    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                      {filteredTools.map((tool) => {
                        const agentTool = localAgentTools.find(
                          (at) => at.tool_id === tool.id,
                        );
                        const requiresApiKey =
                          requiresOrganizationApiKeyBeforeConnect(
                            tool,
                            Boolean(agentTool),
                          );

                        return (
                          <ToolCard
                            key={tool.id}
                            tool={tool}
                            authStatus={
                              agentTool?.auth_status ||
                              AuthStatus.NOT_AUTHENTICATED
                            }
                            connectionStatus={agentTool?.connection_status}
                            tokenExpiresAt={agentTool?.token_expires_at ?? null}
                            isConfigured={!!agentTool}
                            isConnecting={connectingToolId === tool.id}
                            onClick={() => handleToolCardClick(tool)}
                            disabled={!canEdit}
                            requiresApiKey={requiresApiKey}
                            isUnpublished={unpublishedConnectedIds.has(tool.id)}
                            premiumBlocked={premiumToolsBlocked}
                          />
                        );
                      })}
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </AnimatedTabs>

      {agent && (
        <TestCallModal
          open={testCallOpen}
          onOpenChange={setTestCallOpen}
          agentId={agent.id}
          agentName={agent.name}
        />
      )}

      {agent && (
        <AgentDeleteDialog
          open={deleteDialogOpen}
          onOpenChange={setDeleteDialogOpen}
          agent={agent}
          onSuccess={handleDeleteSuccess}
        />
      )}

      {selectedTool && (
        <ToolConfigDrawer
          open={toolDrawerOpen}
          onOpenChange={handleCloseToolDrawer}
          tool={selectedTool}
          agentTool={
            localAgentTools.find((at) => at.tool_id === selectedTool.id) || null
          }
          onSaveConfig={handleSaveToolConfig}
          onToggleFunction={handleToggleFunction}
          onOAuth={handleOAuth}
          onLogout={handleLogout}
          onSetApiKey={handleSetApiKey}
          onDisconnect={() => {
            const agentTool = localAgentTools.find(
              (at) => at.tool_id === selectedTool.id,
            );
            if (agentTool) {
              setDisconnectingToolId(agentTool.id);
              setDisconnectDialogOpen(true);
            }
          }}
          canEdit={canEdit}
          isSaving={updateAgentToolMutation.isPending}
        />
      )}

      {pendingApiKeyTool && (
        <ToolApiKeySetupDialog
          open
          onOpenChange={(open) => {
            if (!open && !configureAgentToolMutation.isPending) {
              setPendingApiKeyTool(null);
            }
          }}
          toolName={pendingApiKeyTool.name}
          onConnect={handleRequiredApiKeyConnect}
          isConnecting={configureAgentToolMutation.isPending}
        />
      )}

      {selectedTool && (
        <ToolDisconnectDialog
          open={disconnectDialogOpen}
          onOpenChange={handleCloseDisconnectDialog}
          onConfirm={() => handleDisconnect(disconnectingToolId || "")}
          toolName={selectedTool.name.replace(/_/g, " ")}
        />
      )}

      <Dialog open={!!pendingTemplate} onOpenChange={(open) => !open && setPendingTemplate(null)}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Replace current instructions?</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">
            Inserting the <span className="font-medium text-foreground">{pendingTemplate?.name}</span> template
            will replace your current agent instructions. This action cannot be undone.
          </p>
          <DialogFooter className="gap-2 sm:gap-0">
            <Button variant="outline" onClick={() => setPendingTemplate(null)}>
              Cancel
            </Button>
            <Button
              onClick={() => {
                if (pendingTemplate) {
                  const markdown = buildMarkdownFromTemplate(pendingTemplate);
                  setAgentForm({
                    ...agentForm,
                    persona: pendingTemplate.persona || agentForm.persona,
                    tone: pendingTemplate.tone || agentForm.tone,
                    instructions_markdown: markdown,
                  });
                  toast.success(`"${pendingTemplate.name}" template inserted`);
                }
                setPendingTemplate(null);
              }}
            >
              Replace instructions
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
