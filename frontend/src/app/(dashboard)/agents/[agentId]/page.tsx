"use client";

import React, { useCallback, useEffect } from "react";
import { useAuth } from "@/contexts/auth-context";
import { useUserPermissions } from "@/hooks/use-user-permissions";
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
} from "@/hooks/use-agent-queries";
import { organizationService } from "@/services/organization-service";
import type { PlatformTool, AgentTool } from "@/types/agent";
import type { Organization } from "@/types/organization";
import { AuthStatus } from "@/types/agent";
import { AgentDeleteDialog } from "@/components/agents/agent-delete-dialog";
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
import { Checkbox } from "@/components/ui/checkbox";
import {
  Bot,
  Settings,
  Save,
  ArrowLeft,
  Loader2,
  Wrench,
} from "lucide-react";
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
  const [disconnectingToolId, setDisconnectingToolId] = React.useState<string | null>(null);
  const [activeTab, setActiveTab] = React.useState("properties");
  const [pendingToolToOpen, setPendingToolToOpen] = React.useState<PlatformTool | null>(null);
  const [connectingToolId, setConnectingToolId] = React.useState<string | null>(null);

  const [toolDrawerOpen, setToolDrawerOpen] = React.useState(false);
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
    system_prompt: "",
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
        system_prompt: agent.system_prompt || "",
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
        {canEdit && (
          <DeleteButton onClick={handleDeleteAgent}>
            Delete Agent
          </DeleteButton>
        )}
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

              <div className="space-y-2">
                <Label htmlFor="prompt">System Prompt</Label>
                <Textarea
                  id="prompt"
                  value={agentForm.system_prompt}
                  onChange={(e) =>
                    setAgentForm({
                      ...agentForm,
                      system_prompt: e.target.value,
                    })
                  }
                  placeholder="You are a helpful customer support agent..."
                  className="min-h-[200px]"
                  disabled={!canEdit}
                />
                <p className="text-xs text-muted-foreground">
                  Instructions for the AI on how to behave
                </p>
              </div>

              <div className="flex items-center space-x-2 pt-2">
                <Checkbox
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
