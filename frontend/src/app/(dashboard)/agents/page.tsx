"use client";

import React, { useMemo, useCallback, useEffect } from "react";
import { useOrganization } from "@/contexts/organization-context";
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
import { useMyAgents, useDeleteAgent } from "@/hooks/use-agent-queries";
import { AgentDeleteDialog } from "@/components/agents/agent-delete-dialog";
import { AgentCard } from "@/components/agents/agent-card";
import type { VoiceAgent } from "@/types/agent";

export default function AgentsPage() {
  const { organizations } = useOrganization();
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

  // Fetch agents with React Query
  const { data: agents = [], isLoading, error } = useMyAgents();

  // Fetch organizations (reuse from context if available, otherwise get all)
  const allOrganizations = useMemo(() => organizations || [], [organizations]);

  // Memoize filtered agents to avoid recalculation on every render
  const filteredAgents = useMemo(() => {
    let filtered = agents;

    if (selectedOrgId !== "all") {
      filtered = filtered.filter(
        (agent) => agent.organization_id === selectedOrgId,
      );
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
  }, [agents, selectedOrgId, searchQuery]);

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
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <div className="bg-primary/10 p-3 rounded-lg">
            <Bot className="h-6 w-6 text-primary" />
          </div>
          <div>
            <h1 className="text-2xl font-bold">Voice Agents</h1>
            <p className="text-sm text-muted-foreground">
              Manage your AI voice agents across all organizations
            </p>
          </div>
        </div>

        <Button onClick={handleAddAgent}>
          <Plus className="h-4 w-4 mr-2" />
          New Agent
        </Button>
      </div>

      <AnimatedTabs
        value={activeTab}
        onValueChange={handleTabChange}
        className="space-y-6"
      >
        <TabsList className="w-full">
          <TabsTrigger value="list">List View</TabsTrigger>
          <TabsTrigger value="grid">Grid View</TabsTrigger>
        </TabsList>

        <TabsContent value="list" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Filter & Search</CardTitle>
              <CardDescription>
                Find agents by organization or name
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex flex-col sm:flex-row gap-4">
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
                <div className="flex-1">
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
                  {searchQuery || selectedOrgId !== "all"
                    ? "No agents match your search or filter criteria."
                    : "You haven't created any voice agents yet."}
                </p>
                <Button onClick={handleAddAgent}>
                  <Plus className="h-4 w-4 mr-2" />
                  Create Your First Agent
                </Button>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-3">
              {filteredAgents.map((agent) => (
                <AgentCard
                  key={agent.id}
                  agent={agent}
                  organizationName={getOrgName(agent.organization_id)}
                  view="list"
                  onDelete={handleDeleteAgent}
                />
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="grid" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Filter & Search</CardTitle>
              <CardDescription>
                Find agents by organization or name
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex flex-col sm:flex-row gap-4">
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
                <div className="flex-1">
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
                  {searchQuery || selectedOrgId !== "all"
                    ? "No agents match your search or filter criteria."
                    : "You haven't created any voice agents yet."}
                </p>
                <Button onClick={handleAddAgent}>
                  <Plus className="h-4 w-4 mr-2" />
                  Create Your First Agent
                </Button>
              </CardContent>
            </Card>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {filteredAgents.map((agent) => (
                <AgentCard
                  key={agent.id}
                  agent={agent}
                  organizationName={getOrgName(agent.organization_id)}
                  view="grid"
                  onDelete={handleDeleteAgent}
                />
              ))}
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
