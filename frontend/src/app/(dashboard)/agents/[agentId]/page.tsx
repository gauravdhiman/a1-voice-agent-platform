"use client";

import React, { useCallback, useEffect } from "react";
import { toast } from "sonner";
import { useAuth } from "@/contexts/auth-context";
import { useUserPermissions } from "@/hooks/use-user-permissions";
import { useRealtime } from "@/hooks/use-realtime";
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
import type { PlatformTool, AgentTool } from "@/types/agent";
import type { Organization } from "@/types/organization";
import { AuthStatus } from "@/types/agent";
import { AgentDeleteDialog } from "@/components/agents/agent-delete-dialog";
import { TestCallModal } from "@/components/agents/test-call-modal";
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
  ToolFilterType,
} from "@/components/tools";
import {
  AnimatedTabs,
  TabsList,
  TabsTrigger,
  TabsContent,
} from "@/components/ui/tabs";
import { Switch } from "@/components/ui/switch";
import { Bot, Settings, Save, ArrowLeft, Loader2, Wrench, Info, Eye, EyeOff, Phone } from "lucide-react";
import { useRouter, useParams, useSearchParams } from "next/navigation";

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
  const [saving, setSaving] = React.useState(false);
  const [localAgentTools, setLocalAgentTools] = React.useState<AgentTool[]>([]);
  const [deleteDialogOpen, setDeleteDialogOpen] = React.useState(false);
  const [disconnectDialogOpen, setDisconnectDialogOpen] = React.useState(false);
  const [disconnectingToolId, setDisconnectingToolId] = React.useState<
    string | null
  >(null);
  const [activeTab, setActiveTab] = React.useState("properties");
  const [pendingToolToOpen, setPendingToolToOpen] =
    React.useState<PlatformTool | null>(null);
  const [connectingToolId, setConnectingToolId] = React.useState<string | null>(
    null,
  );
  const [toolDrawerOpen, setToolDrawerOpen] = React.useState(false);
  const [showSystemPrompt, setShowSystemPrompt] = React.useState(false);
  const [testCallOpen, setTestCallOpen] = React.useState(false);

  // Enable real-time updates for this agent's tools
  useRealtime(agentId, {
    tables: ["agent_tools", "voice_agents"], // Database table is voice_agents, not agents
  });

  const [selectedTool, setSelectedTool] = React.useState<PlatformTool | null>(
    null,
  );
  const [toolSearchQuery, setToolSearchQuery] = React.useState("");
  const [toolFilterType, setToolFilterType] =
    React.useState<ToolFilterType>("all");

  // Agent form state
  const [agentForm, setAgentForm] = React.useState({
    name: "",
    phone_number: "",
    persona: "",
    tone: "",
    mission: "",
    custom_instructions: "",
    is_active: true,
  });

  // Fetch data using React Query
  const {
    data: agent,
    isLoading: agentLoading,
    error: agentError,
  } = useAgent(agentId);
  const { data: platformTools = [], isLoading: toolsLoading } =
    usePlatformTools();
  const { data: agentTools = [], refetch: refetchAgentTools } =
    useAgentTools(agentId);

  // Fetch system prompt preview
  const {
    data: systemPromptPreview,
    isLoading: systemPromptLoading,
  } = useAgentSystemPrompt(agentId);

  // Mutations
  const updateAgentMutation = useUpdateAgent();
  const deleteAgentMutation = useDeleteAgent();
  const toggleFunctionMutation = useToggleFunction();
  const updateAgentToolMutation = useUpdateAgentTool();
  const startOAuthMutation = useStartOAuth();
  const logoutAgentToolMutation = useLogoutAgentTool();
  const deleteAgentToolMutation = useDeleteAgentTool();
  const configureAgentToolMutation = useConfigureAgentTool();

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

  // Update form when agent data changes
  React.useEffect(() => {
    if (agent) {
      setAgentForm({
        name: agent.name,
        phone_number: agent.phone_number || "",
        persona: agent.persona || "",
        tone: agent.tone || "",
        mission: agent.mission || "",
        custom_instructions: agent.custom_instructions || "",
        is_active: agent.is_active,
      });
    }
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
    const tabParam = searchParams.get("tab");
    if (tabParam === "properties" || tabParam === "tools") {
      setActiveTab(tabParam);
    }
  }, [searchParams]);

  const handleTabChange = useCallback(
    (value: string) => {
      setActiveTab(value);
      router.push(`/agents/${agentId}?tab=${value}`, { scroll: false });
    },
    [router, agentId],
  );

  const handleSaveAgent = useCallback(async () => {
    if (!agentId) return;

    setSaving(true);
    try {
      await updateAgentMutation.mutateAsync({
        agentId,
        data: agentForm,
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
    [agentId, localAgentTools, configureAgentToolMutation],
  );

  const handleCloseToolDrawer = useCallback(() => {
    setToolDrawerOpen(false);
    setSelectedTool(null);
    refetchAgentTools();
  }, [refetchAgentTools]);

  const getFilteredTools = useCallback(() => {
    let filtered = platformTools;

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
  }, [platformTools, toolSearchQuery, toolFilterType, localAgentTools]);

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
    <div className="space-y-6">
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
          {canEdit && agent.is_active && (
            <Button
              variant="outline"
              onClick={() => setTestCallOpen(true)}
            >
              <Phone className="h-4 w-4 mr-2" />
              Test Agent
            </Button>
          )}
          {canEdit && (
            <DeleteButton onClick={handleDeleteAgent}>Delete Agent</DeleteButton>
          )}
        </div>
      </div>

      <AnimatedTabs
        value={activeTab}
        onValueChange={handleTabChange}
        className="space-y-6"
      >
        <TabsList className="w-full">
          <TabsTrigger value="properties">Properties</TabsTrigger>
          <TabsTrigger value="tools">Tools</TabsTrigger>
        </TabsList>

        {/* Properties Tab */}
        <TabsContent value="properties">
          <Card>
            <CardHeader className="p-5 pb-3">
              <CardTitle className="flex items-center space-x-2 text-lg">
                <Settings className="h-5 w-5" />
                <span>Agent Properties</span>
              </CardTitle>
              <CardDescription>
                Configure your AI voice agent settings
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

              <div className="space-y-2">
                <Label htmlFor="phone">Phone Number</Label>
                <Input
                  id="phone"
                  value={agentForm.phone_number}
                  onChange={(e) =>
                    setAgentForm({ ...agentForm, phone_number: e.target.value })
                  }
                  placeholder="+1234567890"
                  disabled={!canEdit}
                />
                <p className="text-xs text-muted-foreground">
                  Twilio phone number for this agent
                </p>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="persona">Agent Persona / Role</Label>
                  <Input
                    id="persona"
                    value={agentForm.persona}
                    onChange={(e) =>
                      setAgentForm({ ...agentForm, persona: e.target.value })
                    }
                    placeholder="e.g., Front Desk Coordinator"
                    disabled={!canEdit}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="tone">Communication Tone</Label>
                  <select
                    id="tone"
                    value={agentForm.tone}
                    onChange={(e) =>
                      setAgentForm({ ...agentForm, tone: e.target.value })
                    }
                    className="w-full px-3 py-2 border border-input bg-background rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent disabled:opacity-50"
                    disabled={!canEdit}
                  >
                    <option value="Professional">Professional</option>
                    <option value="Friendly">Friendly</option>
                    <option value="Enthusiastic">Enthusiastic</option>
                    <option value="Minimalist">Minimalist / Formal</option>
                  </select>
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="mission">Key Mission</Label>
                <Textarea
                  id="mission"
                  value={agentForm.mission}
                  onChange={(e) =>
                    setAgentForm({ ...agentForm, mission: e.target.value })
                  }
                  placeholder="What should this agent accomplish?"
                  className="min-h-[80px]"
                  disabled={!canEdit}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="custom_instructions">
                  Additional Instructions
                </Label>
                <Textarea
                  id="custom_instructions"
                  value={agentForm.custom_instructions}
                  onChange={(e) =>
                    setAgentForm({
                      ...agentForm,
                      custom_instructions: e.target.value,
                    })
                  }
                  placeholder={`Add context specific to this agent's role. Include:

• Company policies and procedures (for support agents)
• Unique selling points and differentiators (for sales agents)
• Common customer questions and how to handle them
• Emergency or after-hours protocols
• Specific workflows or escalation procedures
• Any other context that helps this agent handle calls effectively

Example for Sales Agent:
"Always mention our 30-day money-back guarantee. If a customer asks about pricing, emphasize our competitive rates and bundle discounts. For enterprise inquiries, gather company size and current provider before scheduling a demo."

Example for Support Agent:
"For billing issues, verify account details first. If the issue requires escalation, collect callback number and best time to reach them. For technical problems, try basic troubleshooting steps before creating a ticket."`}
                  className="min-h-[200px]"
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
                    <span className="font-medium text-sm">Preview Generated System Prompt</span>
                  </div>
                  <span className="text-xs text-muted-foreground">
                    {showSystemPrompt ? "Click to hide" : "Click to view"}
                  </span>
                </button>

                {showSystemPrompt && (
                  <div className="p-4 bg-slate-50 border-t">
                    <p className="text-sm text-muted-foreground mb-3">
                      This is the system prompt the AI receives based on your organization and agent configuration. It combines your business details, agent persona, and instructions into a comprehensive prompt.
                    </p>
                    {systemPromptLoading ? (
                      <div className="flex items-center justify-center py-8">
                        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                        <span className="ml-2 text-sm text-muted-foreground">Generating preview...</span>
                      </div>
                    ) : systemPromptPreview ? (
                      <div className="bg-white border rounded-md p-4 overflow-x-auto">
                        <pre className="text-xs font-mono text-slate-700 whitespace-pre-wrap">
                          {systemPromptPreview}
                        </pre>
                      </div>
                    ) : (
                      <div className="text-center py-8 text-muted-foreground text-sm">
                        Unable to generate preview. Please ensure organization and agent data is saved.
                      </div>
                    )}
                  </div>
                )}
              </div>

              <div className="flex items-center space-x-2 pt-2">
                <Switch
                  id="active"
                  checked={agentForm.is_active}
                  onCheckedChange={(checked) =>
                    setAgentForm({ ...agentForm, is_active: checked === true })
                  }
                  disabled={!canEdit}
                />
                <Label
                  htmlFor="active"
                  className="text-sm font-normal cursor-pointer"
                >
                  Agent is active and ready to handle calls
                </Label>
              </div>

              {canEdit && (
                <div className="flex space-x-2 pt-4">
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
            </CardContent>
          </Card>
        </TabsContent>

        {/* Tools Tab */}
        <TabsContent value="tools">
          <Card>
            <CardHeader className="p-5 pb-3">
              <CardTitle className="flex items-center space-x-2 text-lg">
                <Wrench className="h-5 w-5" />
                <span>Tool Configuration</span>
              </CardTitle>
              <CardDescription>
                Configure platform tools for {agent.name}
              </CardDescription>
            </CardHeader>
            <CardContent className="p-5 pt-0">
              {toolsLoading ? (
                <div className="flex flex-col items-center justify-center py-12 space-y-4">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
                  <p className="text-sm text-muted-foreground">
                    Loading tools...
                  </p>
                </div>
              ) : platformTools.length === 0 ? (
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
                    totalCount={platformTools.length}
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

      {selectedTool && (
        <ToolDisconnectDialog
          open={disconnectDialogOpen}
          onOpenChange={handleCloseDisconnectDialog}
          onConfirm={() => handleDisconnect(disconnectingToolId || "")}
          toolName={selectedTool.name.replace(/_/g, " ")}
        />
      )}
    </div>
  );
}
