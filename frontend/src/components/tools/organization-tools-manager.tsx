"use client";

import { useMemo, useState } from "react";
import { Eye, EyeOff, Loader2, Search, Server, Wrench } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import {
  useOrganizationTools,
  useSetOrganizationToolVisibility,
} from "@/hooks/use-agent-queries";
import type { PlatformTool } from "@/types/agent";

interface OrganizationToolsManagerProps {
  orgId: string;
  canEdit: boolean;
}

function toolLabel(tool: PlatformTool): string {
  return tool.name.replace(/_/g, " ");
}

/**
 * Manage which published platform tools are available for new agent
 * connections in an organization.
 */
export function OrganizationToolsManager({
  orgId,
  canEdit,
}: OrganizationToolsManagerProps) {
  const [search, setSearch] = useState("");
  const [pendingToolId, setPendingToolId] = useState<string | null>(null);
  const {
    data: tools = [],
    isLoading,
    isError,
  } = useOrganizationTools(orgId, {
    includeHidden: true,
  });
  const visibilityMutation = useSetOrganizationToolVisibility();

  const filteredTools = useMemo(() => {
    const query = search.trim().toLowerCase();
    if (!query) return tools;
    return tools.filter((tool) =>
      [tool.name, tool.description ?? ""].some((value) =>
        value.toLowerCase().includes(query),
      ),
    );
  }, [search, tools]);

  const handleVisibilityChange = (tool: PlatformTool, isVisible: boolean) => {
    setPendingToolId(tool.id);
    visibilityMutation.mutate(
      {
        organizationId: orgId,
        toolId: tool.id,
        isVisible,
      },
      { onSettled: () => setPendingToolId(null) },
    );
  };

  return (
    <Card>
      <CardHeader className="space-y-4">
        <div>
          <CardTitle>Organization Tools</CardTitle>
          <CardDescription className="mt-1">
            Published platform tools are available by default. Hide a tool to
            prevent new agents in this organization from connecting it.
          </CardDescription>
        </div>
        <div className="relative max-w-md">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search organization tools"
            aria-label="Search organization tools"
            className="pl-9"
          />
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="rounded-lg border border-blue-200 bg-blue-50 p-3 text-sm text-blue-900 dark:border-blue-900 dark:bg-blue-950/30 dark:text-blue-100">
          Hiding a tool does not disconnect agents that already use it. Those
          connections remain visible on the agent page with a hidden status.
        </div>

        {isLoading && (
          <div className="grid gap-3 md:grid-cols-2">
            {[0, 1, 2].map((item) => (
              <div
                key={item}
                className="h-28 animate-pulse rounded-lg border bg-muted/40"
              />
            ))}
          </div>
        )}

        {isError && (
          <p className="rounded-lg border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive">
            Organization tools could not be loaded. Refresh and try again.
          </p>
        )}

        {!isLoading && !isError && filteredTools.length === 0 && (
          <p className="rounded-lg border border-dashed p-8 text-center text-sm text-muted-foreground">
            {search.trim()
              ? "No organization tools match your search."
              : "No published tools are available yet."}
          </p>
        )}

        {!isLoading && !isError && filteredTools.length > 0 && (
          <div className="grid gap-3 md:grid-cols-2">
            {filteredTools.map((tool) => {
              const isVisible = tool.is_visible !== false;
              const isPending = pendingToolId === tool.id;

              return (
                <div
                  key={tool.id}
                  className="flex items-start gap-3 rounded-lg border p-4 transition-colors hover:bg-muted/30"
                >
                  <div className="rounded-lg border bg-muted/30 p-2.5">
                    <Wrench className="h-4 w-4 text-muted-foreground" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <h3 className="truncate font-medium capitalize">
                        {toolLabel(tool)}
                      </h3>
                      {tool.tool_source === "mcp" && (
                        <Badge
                          variant="outline"
                          className="h-5 gap-1 text-[10px]"
                        >
                          <Server className="h-3 w-3" />
                          MCP
                        </Badge>
                      )}
                    </div>
                    <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">
                      {tool.description || "No description provided."}
                    </p>
                    <div className="mt-3 flex items-center gap-2 text-xs">
                      {isVisible ? (
                        <>
                          <Eye className="h-3.5 w-3.5 text-emerald-600" />
                          <span className="text-muted-foreground">
                            Visible to agents
                          </span>
                        </>
                      ) : (
                        <>
                          <EyeOff className="h-3.5 w-3.5 text-amber-600" />
                          <span className="text-amber-700 dark:text-amber-300">
                            Hidden from new connections
                          </span>
                        </>
                      )}
                    </div>
                  </div>
                  <div
                    className="flex h-8 w-[4.5rem] shrink-0 items-center justify-end gap-2"
                    aria-busy={isPending}
                    data-testid="organization-tool-visibility-slot"
                  >
                    <span className="flex h-4 w-4 shrink-0 items-center justify-center">
                      {isPending && (
                        <Loader2
                          aria-label="Saving tool visibility"
                          className="h-4 w-4 animate-spin text-muted-foreground"
                        />
                      )}
                    </span>
                    <Switch
                      checked={isVisible}
                      onCheckedChange={(checked) =>
                        handleVisibilityChange(tool, checked)
                      }
                      disabled={!canEdit || isPending}
                      aria-label={`${isVisible ? "Hide" : "Show"} ${toolLabel(tool)}`}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
