"use client";

import React from "react";
import { useRouter } from "next/navigation";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import type { VoiceAgent } from "@/types/agent";
import { getAgentDetailHref } from "@/components/agents/agent-detail-tabs";
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
  /**
   * Whether the current user holds `agent:delete` on the current
   * org. When false, the per-card trash icon is hidden. Defaults
   * to `true` so pre-N1 call sites (test fixtures, anything not yet
   * wired to the permission contract) continue to render every
   * action. The page that mounts the card is the strict gate; the
   * card is permissive by default. N1 browser validation surfaced
   * this leak: a regular org member with no delete permission was
   * seeing the trash icon and clicking it produced a no-op
   * because the page-level `useDeleteAgent` was missing the
   * permission context.
   */
  canDelete?: boolean;
  /**
   * Whether the current user holds `agent:update` on the current
   * org. When false, the Edit button (list view) and Edit icon
   * button (grid view) are hidden. Default `true` for the same
   * backward-compat reason as `canDelete`.
   */
  canEdit?: boolean;
  /**
   * Whether the current user can configure agent tools (Tools
   * button in list view, Configure Tools footer in grid view).
   * Default `true` for the same backward-compat reason.
   */
  canConfigure?: boolean;
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
  canDelete = true,
  canEdit = true,
  canConfigure = true,
}: AgentCardFinalProps) {
  const router = useRouter();

  const handleEdit = (e: React.MouseEvent) => {
    // Don't bubble to the card body click — the Edit button has its
    // own destination and we don't want to navigate twice.
    e.stopPropagation();
    router.push(getAgentDetailHref(agent.id));
  };

  const handleConfigureTools = (e: React.MouseEvent) => {
    e.stopPropagation();
    router.push(getAgentDetailHref(agent.id, "tools"));
  };

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    onDelete(agent);
  };

  // The whole card is clickable: regular members (no Edit/Tools/Trash
  // buttons) use this to open the read-only detail view. The card is
  // a <div role="button"> (not a real <button>) so it can legally
  // contain the inner Edit/Tools/Trash buttons — nesting <button>
  // inside <button> is invalid HTML and the browser silently moves
  // the inner ones out, breaking layout.
  const handleCardClick = () => {
    router.push(getAgentDetailHref(agent.id));
  };
  const handleCardKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      router.push(getAgentDetailHref(agent.id));
    }
  };

  if (view === "list") {
    return (
      <div
        role="button"
        tabIndex={0}
        onClick={handleCardClick}
        onKeyDown={handleCardKeyDown}
        aria-label={`View details for ${agent.name}`}
        className={cn(
          "block w-full text-left rounded-xl border transition-colors hover:border-primary/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary cursor-pointer",
          agent.is_active
            ? "bg-green-50 dark:bg-green-950/20 border-green-200 dark:border-green-800"
            : "bg-red-50 dark:bg-red-950/20 border-red-200 dark:border-red-800 opacity-75",
        )}
      >
        <div className="p-4 sm:p-5">
          <div className="flex min-w-0 flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex min-w-0 w-full items-center gap-4 sm:flex-1">
              <div className="shrink-0 rounded-lg bg-primary/10 p-3">
                <Bot className="h-5 w-5 text-primary" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="mb-2 flex min-w-0 flex-wrap items-center gap-x-3 gap-y-1">
                  <h4 className="min-w-0 max-w-full truncate font-semibold text-base">
                    {agent.name}
                  </h4>
                  <Badge
                    variant={agent.is_active ? "default" : "secondary"}
                    className="h-5 scale-90 origin-left"
                  >
                    {agent.is_active ? "Active" : "Inactive"}
                  </Badge>
                </div>
                <div className="flex min-w-0 flex-wrap items-center gap-x-4 gap-y-1 text-sm text-muted-foreground">
                  {organizationName && (
                    <span className="flex min-w-0 max-w-full items-center">
                      <Building2 className="h-3.5 w-3.5 mr-1.5" />
                      <span className="min-w-0 truncate">
                        {organizationName}
                      </span>
                    </span>
                  )}
                  {agent.phone_number && (
                    <span className="flex min-w-0 max-w-full items-center">
                      <Phone className="h-3.5 w-3.5 mr-1.5" />
                      <span className="break-words">{agent.phone_number}</span>
                    </span>
                  )}
                </div>
              </div>
            </div>
            <div
              className="flex w-full shrink-0 flex-wrap items-center justify-end gap-2 sm:w-auto sm:pl-4"
              data-testid="agent-card-actions"
            >
              {canEdit && (
                <Button
                  size="sm"
                  variant="outline"
                  className="flex-1 sm:flex-none"
                  onClick={handleEdit}
                >
                  <Edit3 className="h-4 w-4 mr-2" />
                  Edit
                </Button>
              )}
              {canConfigure && (
                <Button
                  size="sm"
                  variant="outline"
                  className="flex-1 sm:flex-none"
                  onClick={handleConfigureTools}
                >
                  <Wrench className="h-4 w-4 mr-2" />
                  Tools
                </Button>
              )}
              {canDelete && (
                <Button
                  size="icon"
                  variant="ghost"
                  className="h-9 w-9 text-destructive"
                  onClick={handleDelete}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              )}
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={handleCardClick}
      onKeyDown={handleCardKeyDown}
      aria-label={`View details for ${agent.name}`}
      className={cn(
        "block w-full text-left rounded-xl border transition-colors overflow-hidden border-muted/60 hover:border-primary/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary cursor-pointer",
        agent.is_active
          ? "bg-green-50 dark:bg-green-950/20 border-green-200 dark:border-green-800"
          : "bg-red-50 dark:bg-red-950/20 border-red-200 dark:border-red-800 opacity-75",
      )}
    >
      <div className="p-4">
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
            {canEdit && (
              <Button
                size="icon"
                variant="ghost"
                className="h-8 w-8"
                onClick={handleEdit}
              >
                <Edit3 className="h-4 w-4" />
              </Button>
            )}
            {canDelete && (
              <Button
                size="icon"
                variant="ghost"
                className="h-8 w-8 text-destructive"
                onClick={handleDelete}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            )}
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

        {canConfigure && (
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
        )}
      </div>
    </div>
  );
}
