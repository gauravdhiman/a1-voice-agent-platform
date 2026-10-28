"use client";

import React, { useMemo, useCallback, useEffect } from "react";
import { useOrganization } from "@/contexts/organization-context";
import { useUserPermissions } from "@/hooks/use-user-permissions";
import { useAuth } from "@/contexts/auth-context";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Plus, Filter, Loader2, Bot } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  AnimatedTabs,
  TabsList,
  TabsTrigger,
  TabsContent,
} from "@/components/ui/tabs";
import {
  useMyAgents,
  useOrgAgents,
  useDeleteAgent,
  useAgentToolAttention,
} from "@/hooks/use-agent-queries";
import { AgentDeleteDialog } from "@/components/agents/agent-delete-dialog";
import { AgentCard } from "@/components/agents/agent-card";
import type { VoiceAgent } from "@/types/agent";

export default function AgentsPage() {
  const {
    organizations,
    currentOrganization,
    loading: organizationsLoading,
  } = useOrganization();
  const { user } = useAuth();
  const { canCreateAgent: canCreateOnCurrentOrg } = useUserPermissions();
  // Resolve this role directly from the authenticated user. The permissions
  // facade intentionally scopes most flags to the active organization, but a
  // platform admin remains platform-scoped even when no organization is
  // selected yet.
  const isPlatformAdmin = Boolean(user?.hasRole("platform_admin"));
  // Page-level "New Agent" CTA uses agent:create on the *current* org
  // (from /me.permissions). Regular members have agent:read only.
  const canCreateAgent = canCreateOnCurrentOrg;
  // Per-agent permission helper. Platform admins can act across the
  // platform, while organization admins can act only on agents belonging
  // to the agent's organization. This remains correct if a platform admin
  // uses the cross-organization view.
  const canActOnAgent = useCallback(
    (agent: VoiceAgent): boolean => {
      if (user?.hasRole("platform_admin")) return true;
      if (user?.hasRole("org_admin", agent.organization_id)) return true;
      return false;
    },
    [user],
  );
  const router = useRouter();
  const searchParams = useSearchParams();

  const [selectedOrgId, setSelectedOrgId] = React.useState<string>("all");
  const [searchQuery, setSearchQuery] = React.useState("");
  const [activeTab, setActiveTab] = React.useState("list");

  const [deleteDialogOpen, setDeleteDialogOpen] = React.useState(false);
  const [selectedAgent, setSelectedAgent] = React.useState<VoiceAgent | null>(
    null,
  );

  // Sync tab state with URL
  useEffect(() => {
    const tabParam = searchParams.get("tab");
    if (tabParam === "list" || tabParam === "grid") {
      setActiveTab(tabParam);
    }
  }, [searchParams]);

  const handleTabChange = useCallback(
    (value: string) => {
      setActiveTab(value);
      router.push(`/agents?tab=${value}`, { scroll: false });
    },
    [router],
  );

  // Organization users use the active organization as the source of truth;
  // platform admins retain the cross-organization view and filter.
  const myAgentsQuery = useMyAgents(isPlatformAdmin);
  const orgAgentsQuery = useOrgAgents(currentOrganization?.id ?? "");
  const toolAttentionOrganizationId = isPlatformAdmin
    ? selectedOrgId === "all"
      ? null
      : selectedOrgId
    : (currentOrganization?.id ?? null);
  const agentToolAttentionQuery = useAgentToolAttention(
    toolAttentionOrganizationId,
    isPlatformAdmin || Boolean(currentOrganization?.id),
  );
  const agents = useMemo(
    () => (isPlatformAdmin ? myAgentsQuery.data : orgAgentsQuery.data) ?? [],
    [isPlatformAdmin, myAgentsQuery.data, orgAgentsQuery.data],
  );
  const isLoading =
    organizationsLoading ||
    (isPlatformAdmin ? myAgentsQuery.isLoading : orgAgentsQuery.isLoading);
  const error = isPlatformAdmin ? myAgentsQuery.error : orgAgentsQuery.error;

  // Fetch organizations (reuse from context if available, otherwise get all)
  const allOrganizations = useMemo(() => organizations || [], [organizations]);
  const organizationsById = useMemo(
    () =>
      new Map(
        allOrganizations.map(
          (organization) => [organization.id, organization] as const,
        ),
      ),
    [allOrganizations],
  );
  const toolAttentionByAgentId = useMemo(
    () =>
      new Map(
        (agentToolAttentionQuery.data ?? []).map(
          (summary) => [summary.agent_id, summary] as const,
        ),
      ),
    [agentToolAttentionQuery.data],
  );
  const agentToolsNeedAttention = useCallback(
    (agent: VoiceAgent): boolean => {
      const summary = toolAttentionByAgentId.get(agent.id);
      const organization = organizationsById.get(agent.organization_id);
      return Boolean(summary?.needs_attention) ||
        (summary?.has_resend_email_tool === true &&
          organization?.provider_credentials_status?.resend !== true);
    },
    [organizationsById, toolAttentionByAgentId],
  );

  // Memoize filtered agents to avoid recalculation on every render
  const filteredAgents = useMemo(() => {
    let filtered = agents;

    if (isPlatformAdmin && selectedOrgId !== "all") {
      filtered = filtered.filter(
        (agent) => agent.organization_id === selectedOrgId,
      );
    }

    // The API is already organization-scoped for non-platform users. Keep
    // this check in the view as defense in depth against stale or malformed
    // responses crossing the active-organization boundary.
    if (!isPlatformAdmin) {
      const activeOrganizationId = currentOrganization?.id;
      filtered = activeOrganizationId
        ? filtered.filter(
            (agent) => agent.organization_id === activeOrganizationId,
          )
        : [];
    }

    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(
        (agent) =>
          agent.name.toLowerCase().includes(query) ||
          (agent.phone_number && agent.phone_number.includes(query)),
      );
    }

    return filtered;
  }, [
    agents,
    currentOrganization?.id,
    isPlatformAdmin,
    searchQuery,
    selectedOrgId,
  ]);

  const deleteAgentMutation = useDeleteAgent();

  const handleAddAgent = useCallback(() => {
    router.push("/agents/create");
  }, [router]);

  const handleDeleteAgent = useCallback((agent: VoiceAgent) => {
    setSelectedAgent(agent);
    setDeleteDialogOpen(true);
  }, []);

  const handleDeleteSuccess = useCallback(
    async (agentId: string) => {
      try {
        await deleteAgentMutation.mutateAsync(agentId);
        setDeleteDialogOpen(false);
        setSelectedAgent(null);
      } catch (error) {
        console.error("Failed to delete agent:", error);
        throw error;
      }
    },
    [deleteAgentMutation],
  );

  const getOrgName = useCallback(
    (orgId: string) => {
      const org = allOrganizations.find((o) => o.id === orgId);
      return org?.name || "Unknown Organization";
    },
    [allOrganizations],
  );

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-destructive">Failed to load agents</div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-tour="agents-page">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex min-w-0 items-center gap-3 sm:gap-4">
          <div className="shrink-0 rounded-lg bg-primary/10 p-3">
            <Bot className="h-6 w-6 text-primary" />
          </div>
          <div className="min-w-0">
            <h1 className="text-xl font-bold sm:text-2xl">Voice Agents</h1>
            <p className="text-sm text-muted-foreground">
              {isPlatformAdmin
                ? "Manage your AI voice agents across all organizations"
                : `Manage AI voice agents for ${currentOrganization?.name || "your organization"}`}
            </p>
          </div>
        </div>

        {canCreateAgent && (
          <Button onClick={handleAddAgent} data-tour="agents-create" className="w-full sm:w-auto">
            <Plus className="h-4 w-4 mr-2" />
            New Agent
          </Button>
        )}
      </div>

      <AnimatedTabs
        value={activeTab}
        onValueChange={handleTabChange}
        className="space-y-6"
      >
        <TabsList className="w-full" data-tour="agents-view-toggle">
          <TabsTrigger value="list">List View</TabsTrigger>
          <TabsTrigger value="grid">Grid View</TabsTrigger>
        </TabsList>

        <TabsContent value="list" className="space-y-6">
          <Card data-tour="agents-filters">
            <CardHeader>
              <CardTitle>Filter & Search</CardTitle>
              <CardDescription>
                {isPlatformAdmin
                  ? "Find agents by organization or name"
                  : "Find agents by name in the active organization"}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex flex-col sm:flex-row gap-4">
                {isPlatformAdmin && (
                  <div className="flex-1">
                    <div className="relative">
                      <Filter className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                      <select
                        value={selectedOrgId}
                        onChange={(e) => setSelectedOrgId(e.target.value)}
                        className="w-full pl-10 pr-4 py-2.5 border border-input bg-background rounded-md focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                      >
                        <option value="all">All Organizations</option>
                        {allOrganizations.map((org) => (
                          <option key={org.id} value={org.id}>
                            {org.name}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>
                )}
                <div className={isPlatformAdmin ? "flex-1" : "w-full"}>
                  <input
                    type="text"
                    placeholder="Search agents..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full px-4 py-2.5 border border-input bg-background rounded-md focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                  />
                </div>
              </div>
            </CardContent>
          </Card>

          <div data-tour="agents-results">
            {isLoading ? (
              <div className="flex items-center justify-center py-12">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              <span className="ml-3 text-muted-foreground">
                Loading agents...
              </span>
              </div>
            ) : filteredAgents.length === 0 ? (
              <Card>
                <CardContent className="flex flex-col items-center justify-center py-12">
                  <Bot className="h-12 w-12 text-muted-foreground mb-4 opacity-50" />
                  <h3 className="text-lg font-semibold mb-2">No agents found</h3>
                  <p className="text-muted-foreground text-sm mb-4 text-center max-w-md">
                    {searchQuery || (isPlatformAdmin && selectedOrgId !== "all")
                      ? "No agents match your search or filter criteria."
                      : isPlatformAdmin
                        ? "You haven't created any voice agents yet."
                        : "There are no voice agents in the active organization yet."}
                  </p>
                  {canCreateAgent && (
                    <Button onClick={handleAddAgent}>
                      <Plus className="h-4 w-4 mr-2" />
                      Create Your First Agent
                    </Button>
                  )}
                </CardContent>
              </Card>
            ) : (
              <div className="space-y-3">
                {filteredAgents.map((agent) => {
                  const canAct = canActOnAgent(agent);
                  return (
                    <AgentCard
                      key={agent.id}
                      agent={agent}
                      organizationName={getOrgName(agent.organization_id)}
                      view="list"
                      onDelete={handleDeleteAgent}
                      canDelete={canAct}
                      canEdit={canAct}
                      canConfigure={canAct}
                      toolsNeedAttention={agentToolsNeedAttention(agent)}
                    />
                  );
                })}
              </div>
            )}
          </div>
        </TabsContent>

        <TabsContent value="grid" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Filter & Search</CardTitle>
              <CardDescription>
                {isPlatformAdmin
                  ? "Find agents by organization or name"
                  : "Find agents by name in the active organization"}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex flex-col sm:flex-row gap-4">
                {isPlatformAdmin && (
                  <div className="flex-1">
                    <div className="relative">
                      <Filter className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                      <select
                        value={selectedOrgId}
                        onChange={(e) => setSelectedOrgId(e.target.value)}
                        className="w-full pl-10 pr-4 py-2.5 border border-input bg-background rounded-md focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                      >
                        <option value="all">All Organizations</option>
                        {allOrganizations.map((org) => (
                          <option key={org.id} value={org.id}>
                            {org.name}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>
                )}
                <div className={isPlatformAdmin ? "flex-1" : "w-full"}>
                  <input
                    type="text"
                    placeholder="Search agents..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full px-4 py-2.5 border border-input bg-background rounded-md focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                  />
                </div>
              </div>
            </CardContent>
          </Card>

          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              <span className="ml-3 text-muted-foreground">
                Loading agents...
              </span>
            </div>
          ) : filteredAgents.length === 0 ? (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <Bot className="h-12 w-12 text-muted-foreground mb-4 opacity-50" />
                <h3 className="text-lg font-semibold mb-2">No agents found</h3>
                <p className="text-muted-foreground text-sm mb-4 text-center max-w-md">
                  {searchQuery || (isPlatformAdmin && selectedOrgId !== "all")
                    ? "No agents match your search or filter criteria."
                    : isPlatformAdmin
                      ? "You haven't created any voice agents yet."
                      : "There are no voice agents in the active organization yet."}
                </p>
                {canCreateAgent && (
                  <Button onClick={handleAddAgent}>
                    <Plus className="h-4 w-4 mr-2" />
                    Create Your First Agent
                  </Button>
                )}
              </CardContent>
            </Card>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {filteredAgents.map((agent) => {
                const canAct = canActOnAgent(agent);
                return (
                  <AgentCard
                    key={agent.id}
                    agent={agent}
                    organizationName={getOrgName(agent.organization_id)}
                    view="grid"
                    onDelete={handleDeleteAgent}
                    canDelete={canAct}
                    canEdit={canAct}
                    canConfigure={canAct}
                    toolsNeedAttention={agentToolsNeedAttention(agent)}
                  />
                );
              })}
            </div>
          )}
        </TabsContent>
      </AnimatedTabs>

      {selectedAgent && (
        <AgentDeleteDialog
          open={deleteDialogOpen}
          onOpenChange={setDeleteDialogOpen}
          agent={selectedAgent}
          onSuccess={handleDeleteSuccess}
        />
      )}
    </div>
  );
}
