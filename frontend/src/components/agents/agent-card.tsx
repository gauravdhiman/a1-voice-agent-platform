"use client";

import React from "react";
import { useRouter } from "next/navigation";
import { cn } from "@/lib/utils";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import type { VoiceAgent } from "@/types/agent";
import {
  Bot,
  Phone,
  MessageSquare,
  Building2,
  Edit3,
  Trash2,
  Wrench,
  ChevronRight,
} from "lucide-react";

interface AgentCardProps {
  agent: VoiceAgent;
  organizationName?: string;
  onDelete: (agent: VoiceAgent) => void;
}

interface AgentListCardProps extends AgentCardProps {
  view: "list";
}

interface AgentGridCardProps extends AgentCardProps {
  view: "grid";
}

type AgentCardFinalProps = AgentListCardProps | AgentGridCardProps;

export function AgentCard({
  agent,
  organizationName,
  onDelete,
  view,
}: AgentCardFinalProps) {
  const router = useRouter();

  const handleEdit = () => {
    router.push(`/agents/${agent.id}?tab=properties`);
  };

  const handleConfigureTools = () => {
    router.push(`/agents/${agent.id}?tab=tools`);
  };

  const handleDelete = () => {
    onDelete(agent);
  };

  if (view === "list") {
    return (
      <Card className={cn(
        "hover:border-primary/50 transition-colors",
        agent.is_active
          ? "bg-green-50 dark:bg-green-950/20 border-green-200 dark:border-green-800"
          : "bg-red-50 dark:bg-red-950/20 border-red-200 dark:border-red-800 opacity-75" // Red background for inactive agents
      )}>
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
                    variant={agent.is_active ? "default" : "secondary"}
                    className="h-5 scale-90 origin-left"
                  >
                    {agent.is_active ? "Active" : "Inactive"}
                  </Badge>
                </div>
                <div className="flex items-center space-x-4 text-sm text-muted-foreground">
                  {organizationName && (
                    <span className="flex items-center">
                      <Building2 className="h-3.5 w-3.5 mr-1.5" />
                      <span className="truncate">{organizationName}</span>
                    </span>
                  )}
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
              <Button size="sm" variant="outline" onClick={handleEdit}>
                <Edit3 className="h-4 w-4 mr-2" />
                Edit
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={handleConfigureTools}
              >
                <Wrench className="h-4 w-4 mr-2" />
                Tools
              </Button>
              <Button
                size="icon"
                variant="ghost"
                className="h-9 w-9 text-destructive"
                onClick={handleDelete}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={cn(
      "overflow-hidden border-muted/60 hover:border-primary/50 transition-colors",
      agent.is_active
        ? "bg-green-50 dark:bg-green-950/20 border-green-200 dark:border-green-800"
        : "bg-red-50 dark:bg-red-950/20 border-red-200 dark:border-red-800 opacity-75" // Red background for inactive agents
    )}>
      <CardContent className="p-4">
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
          <div className="flex space-x-1">
            <Button
              size="icon"
              variant="ghost"
              className="h-8 w-8"
              onClick={handleEdit}
            >
              <Edit3 className="h-4 w-4" />
            </Button>
            <Button
              size="icon"
              variant="ghost"
              className="h-8 w-8 text-destructive"
              onClick={handleDelete}
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        </div>

        <div className="space-y-2 mt-4">
          {organizationName && (
            <div className="flex items-center text-sm">
              <Building2 className="h-3.5 w-3.5 mr-2 text-muted-foreground" />
              <span className="truncate">{organizationName}</span>
            </div>
          )}
          <div className="flex items-center text-sm">
            <Phone className="h-3.5 w-3.5 mr-2 text-muted-foreground" />
            <span className="truncate">
              {agent.phone_number || "No phone assigned"}
            </span>
          </div>
          <div className="flex items-center text-sm">
            <MessageSquare className="h-3.5 w-3.5 mr-2 text-muted-foreground" />
            <span className="truncate text-xs italic text-muted-foreground">
              {agent.system_prompt
                ? "Custom prompt configured"
                : "Using default prompt"}
            </span>
          </div>
        </div>

        <Separator className="my-4" />

        <Button
          variant="outline"
          size="sm"
          className="w-full text-xs h-8"
          onClick={handleConfigureTools}
        >
          <Wrench className="h-3.5 w-3.5 mr-2" />
          Configure Tools
          <ChevronRight className="h-3.5 w-3.5 ml-2" />
        </Button>
      </CardContent>
    </Card>
  );
}
