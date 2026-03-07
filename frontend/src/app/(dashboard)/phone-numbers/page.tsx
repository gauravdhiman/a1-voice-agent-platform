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
import { Plus, Filter, Loader2, Phone, Bot } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  AnimatedTabs,
  TabsList,
  TabsTrigger,
  TabsContent,
} from "@/components/ui/tabs";
import { useMyAgents } from "@/hooks/use-agent-queries";
import type { VoiceAgent } from "@/types/agent";

interface PhoneNumberCardProps {
  agent: VoiceAgent;
  organizationName: string;
  onEdit: (agent: VoiceAgent) => void;
}

function PhoneNumberCard({
  agent,
  organizationName,
  onEdit,
}: PhoneNumberCardProps) {
  const router = useRouter();

  const handleEdit = () => {
    onEdit(agent);
  };

  const handleConfigure = () => {
    router.push(`/agents/${agent.id}?tab=tools`);
  };

  return (
    <Card
      className={
        agent.is_active
          ? "bg-green-50 dark:bg-green-950/20 border-green-200 dark:border-green-800"
          : "bg-red-50 dark:bg-red-950/20 border-red-200 dark:border-red-800 opacity-75"
      }
    >
      <CardContent className="p-5">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4 flex-1">
            <div className="bg-primary/10 p-3 rounded-lg">
              <Phone className="h-5 w-5 text-primary" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center space-x-3 mb-2">
                <h4 className="font-semibold text-base truncate">
                  {agent.phone_number}
                </h4>
              </div>
              <div className="flex items-center space-x-4 text-sm text-muted-foreground">
                <span className="flex items-center">
                  <Bot className="h-3.5 w-3.5 mr-1.5" />
                  <span className="truncate">{agent.name}</span>
                </span>
                <span className="flex items-center">
                  <span className="truncate">{organizationName}</span>
                </span>
              </div>
            </div>
          </div>
          <div className="flex items-center space-x-2 ml-4">
            <Button size="sm" variant="outline" onClick={handleEdit}>
              Edit Agent
            </Button>
            <Button size="sm" variant="outline" onClick={handleConfigure}>
              Configure
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export default function PhoneNumbersPage() {
  const { organizations } = useOrganization();
  const router = useRouter();
  const searchParams = useSearchParams();

  const [selectedOrgId, setSelectedOrgId] = React.useState<string>("all");
  const [searchQuery, setSearchQuery] = React.useState("");
  const [activeTab, setActiveTab] = React.useState("list");

  useEffect(() => {
    const tabParam = searchParams.get("tab");
    if (tabParam === "list" || tabParam === "grid") {
      setActiveTab(tabParam);
    }
  }, [searchParams]);

  const handleTabChange = useCallback(
    (value: string) => {
      setActiveTab(value);
      router.push(`/phone-numbers?tab=${value}`, { scroll: false });
    },
    [router],
  );

  const { data: agents = [], isLoading, error } = useMyAgents();

  const allOrganizations = useMemo(() => organizations || [], [organizations]);

  const agentsWithPhoneNumbers = useMemo(
    () => agents.filter((agent) => agent.phone_number),
    [agents],
  );

  const filteredAgents = useMemo(() => {
    let filtered = agentsWithPhoneNumbers;

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
  }, [agentsWithPhoneNumbers, selectedOrgId, searchQuery]);

  const handleAddAgent = useCallback(() => {
    router.push("/agents/create");
  }, [router]);

  const handleEditAgent = useCallback((agent: VoiceAgent) => {
    router.push(`/agents/${agent.id}?tab=properties`);
  }, [router]);

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
        <div className="text-destructive">Failed to load phone numbers</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <div className="bg-primary/10 p-3 rounded-lg">
            <Phone className="h-6 w-6 text-primary" />
          </div>
          <div>
            <h1 className="text-2xl font-bold">Phone Numbers</h1>
            <p className="text-sm text-muted-foreground">
              Manage phone numbers across all organizations
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
                Find phone numbers by organization or number
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
                    placeholder="Search by phone number or agent name..."
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
                Loading phone numbers...
              </span>
            </div>
          ) : filteredAgents.length === 0 ? (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <Phone className="h-12 w-12 text-muted-foreground mb-4 opacity-50" />
                <h3 className="text-lg font-semibold mb-2">
                  No phone numbers found
                </h3>
                <p className="text-muted-foreground text-sm mb-4 text-center max-w-md">
                  {searchQuery || selectedOrgId !== "all"
                    ? "No phone numbers match your search or filter criteria."
                    : "You haven't configured any phone numbers yet."}
                </p>
                <Button onClick={handleAddAgent}>
                  <Plus className="h-4 w-4 mr-2" />
                  Create Your First Agent with Phone
                </Button>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-3">
              {filteredAgents.map((agent) => (
                <PhoneNumberCard
                  key={agent.id}
                  agent={agent}
                  organizationName={getOrgName(agent.organization_id)}
                  onEdit={handleEditAgent}
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
                Find phone numbers by organization or number
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
                    placeholder="Search by phone number or agent name..."
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
                Loading phone numbers...
              </span>
            </div>
          ) : filteredAgents.length === 0 ? (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <Phone className="h-12 w-12 text-muted-foreground mb-4 opacity-50" />
                <h3 className="text-lg font-semibold mb-2">
                  No phone numbers found
                </h3>
                <p className="text-muted-foreground text-sm mb-4 text-center max-w-md">
                  {searchQuery || selectedOrgId !== "all"
                    ? "No phone numbers match your search or filter criteria."
                    : "You haven't configured any phone numbers yet."}
                </p>
                <Button onClick={handleAddAgent}>
                  <Plus className="h-4 w-4 mr-2" />
                  Create Your First Agent with Phone
                </Button>
              </CardContent>
            </Card>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {filteredAgents.map((agent) => (
                <PhoneNumberCard
                  key={agent.id}
                  agent={agent}
                  organizationName={getOrgName(agent.organization_id)}
                  onEdit={handleEditAgent}
                />
              ))}
            </div>
          )}
        </TabsContent>
      </AnimatedTabs>
    </div>
  );
}
