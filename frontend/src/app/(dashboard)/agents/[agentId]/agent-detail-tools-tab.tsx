"use client";

import * as React from "react";
import dynamic from "next/dynamic";
import { toast } from "sonner";
import { Info, Wrench } from "lucide-react";

import { useRealtime } from "@/hooks/use-realtime";
import {
  useAgentTools,
  useConfigureAgentTool,
  useDeleteAgentTool,
  useLogoutAgentTool,
  usePlatformTools,
  useStartOAuth,
  useToggleFunction,
  useUpdateAgentTool,
} from "@/hooks/use-agent-queries";
import { agentService } from "@/services/agent-service";
import { billingService } from "@/services/billing-service";
import { buildAgentToolsDisplay } from "@/components/tools/tools-display";
import {
  isResendEmailConfigurationReady,
  RESEND_EMAIL_TOOL_NAME,
} from "@/components/tools/resend-email-config";
import { ToolCard } from "@/components/tools/tool-card";
import {
  DEFAULT_TOOL_FILTER_TYPE,
  shouldShowSeeAllToolsPrompt,
  ToolFilters,
  type ToolFilterType,
} from "@/components/tools/tool-filters";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { AgentTool, PlatformTool, VoiceAgent } from "@/types/agent";
import { AuthStatus, ConnectionStatus } from "@/types/agent";
import type { OrgEntitlements } from "@/types/billing";
import type { Organization } from "@/types/organization";

const ToolConfigDrawer = dynamic(
  () =>
    import("@/components/tools/tool-config-drawer").then(
      (module) => module.ToolConfigDrawer,
    ),
  { ssr: false },
);
const ToolApiKeySetupDialog = dynamic(
  () =>
    import("@/components/tools/tool-api-key-setup-dialog").then(
      (module) => module.ToolApiKeySetupDialog,
    ),
  { ssr: false },
);
const ToolDisconnectDialog = dynamic(
  () =>
    import("@/components/tools/tool-disconnect-dialog").then(
      (module) => module.ToolDisconnectDialog,
    ),
  { ssr: false },
);

const AGENT_REALTIME_TABLES = ["agent_tools", "voice_agents"];
const EMPTY_AGENT_TOOLS: AgentTool[] = [];

/** Whether a new MCP connection must collect an organization API key first. */
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

interface AgentDetailToolsTabProps {
  agent: VoiceAgent;
  organization: Organization | null;
  canEdit: boolean;
}

/** Tool catalog and agent-tool configuration, loaded only on demand. */
export function AgentDetailToolsTab({
  agent,
  organization,
  canEdit,
}: AgentDetailToolsTabProps) {
  const [localAgentTools, setLocalAgentTools] = React.useState<AgentTool[]>(
    EMPTY_AGENT_TOOLS,
  );
  const [selectedTool, setSelectedTool] = React.useState<PlatformTool | null>(
    null,
  );
  const [toolSearchQuery, setToolSearchQuery] = React.useState("");
  const [toolFilterType, setToolFilterType] =
    React.useState<ToolFilterType>(DEFAULT_TOOL_FILTER_TYPE);
  const [pendingToolToOpen, setPendingToolToOpen] =
    React.useState<PlatformTool | null>(null);
  const [pendingApiKeyTool, setPendingApiKeyTool] =
    React.useState<PlatformTool | null>(null);
  const [connectingToolId, setConnectingToolId] = React.useState<string | null>(
    null,
  );
  const [toolDrawerOpen, setToolDrawerOpen] = React.useState(false);
  const [disconnectDialogOpen, setDisconnectDialogOpen] = React.useState(false);
  const [disconnectingToolId, setDisconnectingToolId] = React.useState<
    string | null
  >(null);
  const [orgEntitlements, setOrgEntitlements] =
    React.useState<OrgEntitlements | null>(null);

  useRealtime(agent.id, { tables: AGENT_REALTIME_TABLES });

  const { data: platformTools = [], isLoading: toolsLoading } =
    usePlatformTools(true, { enabled: true });
  const { data: agentToolsData, refetch: refetchAgentTools } = useAgentTools(
    agent.id,
    true,
  );
  const agentTools = agentToolsData ?? EMPTY_AGENT_TOOLS;

  React.useEffect(() => {
    setLocalAgentTools(agentTools);
  }, [agentTools]);

  React.useEffect(() => {
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
  }, [agent.organization_id]);

  const premiumToolsBlocked =
    !orgEntitlements?.features["premium_tools"]?.effective_value;

  const toggleFunctionMutation = useToggleFunction();
  const updateAgentToolMutation = useUpdateAgentTool();
  const startOAuthMutation = useStartOAuth();
  const logoutAgentToolMutation = useLogoutAgentTool();
  const deleteAgentToolMutation = useDeleteAgentTool();
  const configureAgentToolMutation = useConfigureAgentTool();

  React.useEffect(() => {
    if (!pendingToolToOpen) return;
    const newAgentTool = localAgentTools.find(
      (agentTool) => agentTool.tool_id === pendingToolToOpen.id,
    );
    if (!newAgentTool) return;
    setSelectedTool(pendingToolToOpen);
    setToolDrawerOpen(true);
    setPendingToolToOpen(null);
    setConnectingToolId(null);
  }, [localAgentTools, pendingToolToOpen]);

  const handleToggleFunction = React.useCallback(
    async (toolId: string, functionName: string, isChecked: boolean) => {
      const existingAgentTool = localAgentTools.find(
        (agentTool) => agentTool.tool_id === toolId,
      );
      if (!existingAgentTool) return;

      const currentUnselected = existingAgentTool.unselected_functions || [];
      const newUnselected = isChecked
        ? currentUnselected.filter((name) => name !== functionName)
        : currentUnselected.includes(functionName)
          ? currentUnselected
          : [...currentUnselected, functionName];

      await toggleFunctionMutation.mutateAsync({
        agentToolId: existingAgentTool.id,
        unselectedFunctions: newUnselected,
      });
    },
    [localAgentTools, toggleFunctionMutation],
  );

  const handleToggleAllFunctions = React.useCallback(
    async (toolId: string, functionNames: string[], isEnabled: boolean) => {
      const existingAgentTool = localAgentTools.find(
        (agentTool) => agentTool.tool_id === toolId,
      );
      if (!existingAgentTool) return;

      await toggleFunctionMutation.mutateAsync({
        agentToolId: existingAgentTool.id,
        unselectedFunctions: isEnabled ? [] : functionNames,
        isBulk: true,
      });
    },
    [localAgentTools, toggleFunctionMutation],
  );

  const handleSaveToolConfig = React.useCallback(
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

  const handleOAuth = React.useCallback(
    async (toolName: string) => {
      try {
        await startOAuthMutation.mutateAsync({ toolName, agentId: agent.id });
      } catch (error) {
        console.error("OAuth failed:", error);
      }
    },
    [agent.id, startOAuthMutation],
  );

  const handleLogout = React.useCallback(
    async (agentToolId: string) => {
      try {
        await logoutAgentToolMutation.mutateAsync(agentToolId);
      } catch (error) {
        console.error("Failed to log out:", error);
      }
    },
    [logoutAgentToolMutation],
  );

  const handleSetApiKey = React.useCallback(
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

  const handleDisconnect = React.useCallback(
    async (agentToolId: string) => {
      try {
        await deleteAgentToolMutation.mutateAsync(agentToolId);
        setLocalAgentTools((previous) =>
          previous.filter((tool) => tool.id !== agentToolId),
        );
      } catch (error) {
        console.error("Failed to disconnect:", error);
        throw error;
      }
    },
    [deleteAgentToolMutation],
  );

  const handleCloseDisconnectDialog = React.useCallback(() => {
    setDisconnectDialogOpen(false);
    setDisconnectingToolId(null);
    setToolDrawerOpen(false);
  }, []);

  const handleToolCardClick = React.useCallback(
    async (tool: PlatformTool) => {
      const existingAgentTool = localAgentTools.find(
        (agentTool) => agentTool.tool_id === tool.id,
      );

      if (existingAgentTool) {
        setSelectedTool(tool);
        setToolDrawerOpen(true);
        return;
      }

      if (requiresOrganizationApiKeyBeforeConnect(tool, false)) {
        setPendingApiKeyTool(tool);
        return;
      }

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
          agent_id: agent.id,
          tool_id: tool.id,
          is_enabled: true,
        });
      } catch (error) {
        console.error("Failed to configure tool:", error);
        setPendingToolToOpen(null);
        setConnectingToolId(null);
      }
    },
    [
      agent.id,
      configureAgentToolMutation,
      localAgentTools,
      premiumToolsBlocked,
    ],
  );

  const handleRequiredApiKeyConnect = React.useCallback(
    async (apiKey: string) => {
      if (!pendingApiKeyTool) return;

      const tool = pendingApiKeyTool;
      try {
        setConnectingToolId(tool.id);
        setPendingToolToOpen(tool);
        await configureAgentToolMutation.mutateAsync({
          agent_id: agent.id,
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
    [agent.id, configureAgentToolMutation, pendingApiKeyTool],
  );

  const handleCloseToolDrawer = React.useCallback(() => {
    setToolDrawerOpen(false);
    setSelectedTool(null);
    refetchAgentTools();
  }, [refetchAgentTools]);

  const { allTools, unpublishedConnectedIds } = React.useMemo(
    () => buildAgentToolsDisplay(platformTools, localAgentTools),
    [localAgentTools, platformTools],
  );

  const connectedToolIds = React.useMemo(
    () => new Set(localAgentTools.map((agentTool) => agentTool.tool_id)),
    [localAgentTools],
  );

  const connectedToolCount = React.useMemo(
    () => allTools.filter((tool) => connectedToolIds.has(tool.id)).length,
    [allTools, connectedToolIds],
  );

  const filteredTools = React.useMemo(() => {
    let filtered = allTools;
    const query = toolSearchQuery.trim().toLowerCase();

    if (query) {
      filtered = filtered.filter(
        (tool) =>
          tool.name.toLowerCase().includes(query) ||
          tool.description?.toLowerCase().includes(query),
      );
    }

    if (toolFilterType === "connected") {
      filtered = filtered.filter((tool) => connectedToolIds.has(tool.id));
    } else if (toolFilterType === "not_connected") {
      filtered = filtered.filter((tool) => !connectedToolIds.has(tool.id));
    }

    return filtered;
  }, [allTools, connectedToolIds, toolFilterType, toolSearchQuery]);

  const showSeeAllToolsPrompt = shouldShowSeeAllToolsPrompt({
    filterType: toolFilterType,
    connectedToolCount,
    searchQuery: toolSearchQuery,
  });

  return (
    <>
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
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
              <p className="text-sm text-muted-foreground">Loading tools...</p>
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
              <div className="bg-amber-50 border border-amber-200 rounded-md p-3 flex items-start gap-2">
                <Info className="h-4 w-4 text-amber-600 mt-0.5 flex-shrink-0" />
                <div className="text-sm text-amber-800 space-y-1">
                  <p className="font-medium">
                    Best Practice: Keep Tool Selection Focused
                  </p>
                  <p>
                    Only enable the tools your agent truly needs. Too many tools
                    can confuse the AI and reduce response quality. For each
                    tool set you connect, selectively enable only the specific
                    functions required for your use case.
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
                    {showSeeAllToolsPrompt
                      ? "No tools are connected to this agent yet."
                      : "No tools match your current filters."}
                  </p>
                  {showSeeAllToolsPrompt && (
                    <Button
                      type="button"
                      variant="outline"
                      className="mt-4"
                      onClick={() => setToolFilterType("all")}
                    >
                      See all tools
                    </Button>
                  )}
                </div>
              ) : (
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                  {filteredTools.map((tool) => {
                    const agentTool = localAgentTools.find(
                      (candidate) => candidate.tool_id === tool.id,
                    );
                    const requiresApiKey =
                      requiresOrganizationApiKeyBeforeConnect(
                        tool,
                        Boolean(agentTool),
                      );
                    const resendConfigurationRequired =
                      tool.name === RESEND_EMAIL_TOOL_NAME &&
                      Boolean(agentTool) &&
                      !isResendEmailConfigurationReady(
                        agentTool?.config,
                        organization?.provider_credentials_status?.resend,
                      );
                    const backendConfigurationRequired =
                      agentTool?.connection_status ===
                      ConnectionStatus.CONFIGURATION_REQUIRED;

                    return (
                      <ToolCard
                        key={tool.id}
                        tool={tool}
                        authStatus={
                          agentTool?.auth_status || AuthStatus.NOT_AUTHENTICATED
                        }
                        connectionStatus={
                          resendConfigurationRequired ||
                          backendConfigurationRequired
                            ? ConnectionStatus.CONFIGURATION_REQUIRED
                            : agentTool?.connection_status
                        }
                        configurationIssues={agentTool?.configuration_issues}
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

      {selectedTool && (
        <ToolConfigDrawer
          open={toolDrawerOpen}
          onOpenChange={handleCloseToolDrawer}
          tool={selectedTool}
          agentTool={
            localAgentTools.find(
              (agentTool) => agentTool.tool_id === selectedTool.id,
            ) || null
          }
          organizationId={agent.organization_id}
          resendCredentialConfigured={
            organization?.provider_credentials_status?.resend
          }
          onSaveConfig={handleSaveToolConfig}
          onToggleFunction={handleToggleFunction}
          onToggleAllFunctions={handleToggleAllFunctions}
          onOAuth={handleOAuth}
          onLogout={handleLogout}
          onSetApiKey={handleSetApiKey}
          onDisconnect={() => {
            const agentTool = localAgentTools.find(
              (candidate) => candidate.tool_id === selectedTool.id,
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
    </>
  );
}
