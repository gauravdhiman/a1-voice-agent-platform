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
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Bot,
  Phone,
  MessageSquare,
  Plus,
  Building2,
  Filter,
  Trash2,
  Settings,
  ChevronRight,
  Loader2,
} from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { toast } from "sonner";
import {
  AnimatedTabs,
  TabsList,
  TabsTrigger,
  TabsContent,
} from "@/components/ui/tabs";
import {
  useMyAgents,
  useCreateAgent,
  useDeleteAgent,
} from "@/hooks/use-agent-queries";
import { AgentDeleteDialog } from "@/components/agents/agent-delete-dialog";
import type { VoiceAgent } from "@/types/agent";

export default function AgentsPage() {
  const { organizations, currentOrganization } = useOrganization();
  const router = useRouter();
  const searchParams = useSearchParams();

  const [selectedOrgId, setSelectedOrgId] = React.useState<string>("all");
  const [searchQuery, setSearchQuery] = React.useState("");
  const [activeTab, setActiveTab] = React.useState("list");

  // Agent creation state
  const [agentDialogOpen, setAgentDialogOpen] = React.useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = React.useState(false);
  const [selectedAgent, setSelectedAgent] = React.useState<VoiceAgent | null>(
    null,
  );
  const [agentForm, setAgentForm] = React.useState({
    name: "",
    phone_number: "",
    system_prompt: "",
    is_active: true,
    organization_id: "",
  });

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

  // Mutation for creating agents
  const createAgentMutation = useCreateAgent();
  const deleteAgentMutation = useDeleteAgent();

  const handleAddAgent = useCallback(() => {
    setAgentForm({
      name: "",
      phone_number: "",
      system_prompt: "",
      is_active: true,
      organization_id: currentOrganization?.id || "",
    });
    setAgentDialogOpen(true);
  }, [currentOrganization?.id]);

  const handleSaveAgent = useCallback(async () => {
    if (!agentForm.name) {
      toast.error("Agent name is required");
      return;
    }

    if (!agentForm.organization_id) {
      toast.error("Please select an organization");
      return;
    }

    try {
      await createAgentMutation.mutateAsync({
        name: agentForm.name,
        phone_number: agentForm.phone_number,
        system_prompt: agentForm.system_prompt,
        is_active: agentForm.is_active,
        organization_id: agentForm.organization_id,
      });
      setAgentDialogOpen(false);
    } catch (error) {
      console.error("Failed to create agent:", error);
    }
  }, [agentForm, createAgentMutation]);

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

  const handleConfigureAgent = useCallback(
    (agentId: string) => {
      router.push(`/agents/${agentId}`);
    },
    [router],
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
                <Card
                  key={agent.id}
                  className="hover:border-primary/50 transition-colors"
                >
                  <CardContent className="p-5">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-4 flex-1">
                        <div className="bg-primary/10 p-3 rounded-lg">
                          <Bot className="h-5 w-5 text-primary" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center space-x-3 mb-2">
                            <h4 className="font-semibold text-base truncate">
                              {agent.name}
                            </h4>
                            <Badge
                              variant={
                                agent.is_active ? "default" : "secondary"
                              }
                              className="h-5 scale-90 origin-left"
                            >
                              {agent.is_active ? "Active" : "Inactive"}
                            </Badge>
                          </div>
                          <div className="flex items-center space-x-4 text-sm text-muted-foreground">
                            <span className="flex items-center">
                              <Building2 className="h-3.5 w-3.5 mr-1.5" />
                              <span className="truncate">
                                {getOrgName(agent.organization_id)}
                              </span>
                            </span>
                            {agent.phone_number && (
                              <span className="flex items-center">
                                <Phone className="h-3.5 w-3.5 mr-1.5" />
                                <span>{agent.phone_number}</span>
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center space-x-2 ml-4">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleConfigureAgent(agent.id)}
                        >
                          <Settings className="h-4 w-4 mr-2" />
                          Configure
                        </Button>
                        <Button
                          size="icon"
                          variant="ghost"
                          className="h-9 w-9 text-destructive"
                          onClick={() => handleDeleteAgent(agent)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
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
                <Card
                  key={agent.id}
                  className="overflow-hidden hover:border-primary/50 transition-colors"
                >
                  <CardContent className="p-5">
                    <div className="flex justify-between items-start mb-3">
                      <div className="flex-1 min-w-0">
                        <h4 className="font-semibold text-base truncate mb-2">
                          {agent.name}
                        </h4>
                        <div className="flex items-center space-x-2">
                          <Badge
                            variant={agent.is_active ? "default" : "secondary"}
                            className="h-5 scale-90 origin-left"
                          >
                            {agent.is_active ? "Active" : "Inactive"}
                          </Badge>
                        </div>
                      </div>
                      <div className="flex space-x-1 ml-2">
                        <Button
                          size="icon"
                          variant="ghost"
                          className="h-8 w-8 text-destructive"
                          onClick={() => handleDeleteAgent(agent)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>

                    <div className="space-y-2 mt-4">
                      <div className="flex items-center text-sm">
                        <Building2 className="h-3.5 w-3.5 mr-2 text-muted-foreground" />
                        <span className="truncate">
                          {getOrgName(agent.organization_id)}
                        </span>
                      </div>
                      {agent.phone_number && (
                        <div className="flex items-center text-sm">
                          <Phone className="h-3.5 w-3.5 mr-2 text-muted-foreground" />
                          <span className="truncate">{agent.phone_number}</span>
                        </div>
                      )}
                      <div className="flex items-center text-sm">
                        <MessageSquare className="h-3.5 w-3.5 mr-2 text-muted-foreground" />
                        <span className="truncate text-xs italic text-muted-foreground">
                          {agent.system_prompt
                            ? "Custom prompt configured"
                            : "Using default prompt"}
                        </span>
                      </div>
                    </div>

                    <Button
                      variant="outline"
                      size="sm"
                      className="w-full text-xs h-8 mt-4"
                      onClick={() => handleConfigureAgent(agent.id)}
                    >
                      Configure
                      <ChevronRight className="h-3.5 w-3.5 ml-2" />
                    </Button>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>
      </AnimatedTabs>

      {/* Agent Create Dialog */}
      <Dialog open={agentDialogOpen} onOpenChange={setAgentDialogOpen}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>Create New Voice Agent</DialogTitle>
            <DialogDescription>
              Create a new AI voice agent for your organization.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="agent-org">Organization</Label>
              <select
                id="agent-org"
                value={agentForm.organization_id}
                onChange={(e) =>
                  setAgentForm({
                    ...agentForm,
                    organization_id: e.target.value,
                  })
                }
                className="w-full px-3 py-2.5 border border-input bg-background rounded-md focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
              >
                <option value="">Select an organization</option>
                {allOrganizations.map((org) => (
                  <option key={org.id} value={org.id}>
                    {org.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="agent-name">Name</Label>
              <Input
                id="agent-name"
                value={agentForm.name}
                onChange={(e) =>
                  setAgentForm({ ...agentForm, name: e.target.value })
                }
                placeholder="Support Agent, Sales Bot, etc."
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="agent-phone">Phone Number (Optional)</Label>
              <Input
                id="agent-phone"
                value={agentForm.phone_number}
                onChange={(e) =>
                  setAgentForm({ ...agentForm, phone_number: e.target.value })
                }
                placeholder="+1234567890"
              />
              <p className="text-xs text-muted-foreground">
                Twilio phone number for this agent
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="agent-prompt">System Prompt (Optional)</Label>
              <Textarea
                id="agent-prompt"
                value={agentForm.system_prompt}
                onChange={(e) =>
                  setAgentForm({ ...agentForm, system_prompt: e.target.value })
                }
                placeholder="You are a helpful customer support agent..."
                className="min-h-[150px]"
              />
              <p className="text-xs text-muted-foreground">
                Instructions for the AI on how to behave
              </p>
            </div>
            <div className="flex items-center space-x-2 pt-2">
              <Checkbox
                id="agent-active"
                checked={agentForm.is_active}
                onCheckedChange={(checked) =>
                  setAgentForm({ ...agentForm, is_active: checked === true })
                }
              />
              <Label
                htmlFor="agent-active"
                className="text-sm font-normal cursor-pointer"
              >
                Agent is active and ready to handle calls
              </Label>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setAgentDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleSaveAgent}
              disabled={
                createAgentMutation.isPending ||
                !agentForm.name ||
                !agentForm.organization_id
              }
            >
              {createAgentMutation.isPending ? "Creating..." : "Create Agent"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

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
