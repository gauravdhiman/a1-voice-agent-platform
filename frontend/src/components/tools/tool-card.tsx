import * as React from "react";
import { cn } from "@/lib/utils";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Wrench,
  ShieldCheck,
  Clock,
  Loader2,
  XCircle,
  Server,
  EyeOff,
  Crown,
  Lock,
} from "lucide-react";
import { AuthStatus, ConnectionStatus } from "@/types/agent";
import { useLiveTime, formatTimeUntilExpiry } from "@/hooks/use-live-time";
import { ExpandableDescription } from "@/components/tools/expandable-description";

interface ToolCardFunctionCatalog {
  functions: Array<{ name: string }>;
}

export interface ToolCardProps {
  tool: {
    id: string;
    name: string;
    description: string | null;
    /** Origin of the tool — rendered as an "MCP" badge when set to "mcp". */
    tool_source?: "legacy" | "mcp";
    /** Authentication mode, used to explain why a catalog is unavailable. */
    auth_type?: string | null;
    /** Streamable-HTTP URL of the remote MCP server (shown under the name). */
    mcp_server_url?: string | null;
    /** Public MCP function catalog discovered by a platform administrator. */
    tool_functions_schema?: ToolCardFunctionCatalog | null;
    /**
     * Premium tools require the org's plan to entitle the ``premium_tools``
     * feature. They stay visible with a badge; the connect action is replaced
     * with a locked upgrade hint (the API enforces the same gate).
     */
    is_premium?: boolean;
  };
  authStatus: AuthStatus;
  tokenExpiresAt: number | null;
  connectionStatus?: ConnectionStatus;
  isConfigured?: boolean;
  isConnecting?: boolean;
  onClick: () => void;
  disabled?: boolean;
  /**
   * True when this org's plan does NOT entitle the ``premium_tools`` feature.
   * Premium tools render a locked action instead of Connect; the card is
   * still clickable to view details.
   */
  premiumBlocked?: boolean;
  className?: string;
  /**
   * True when this tool is connected to the agent but no longer published in
   * the platform catalog (`platform_tools.is_published = false`). The worker
   * still loads it for the agent (it joins `agent_tools`, not `is_published`),
   * so the agent keeps the tool at runtime — this flag surfaces that state in
   * the UI so the org admin knows the tool is mapped but unavailable to new
   * agents. Renders an amber "Unpublished" pill + an inline note. RFC §6.6.
   */
  isUnpublished?: boolean;
  /**
   * True when an unconnected MCP tool needs an organization API key before it
   * can be attached because no platform fallback is available.
   */
  requiresApiKey?: boolean;
}

export function ToolCard({
  tool,
  authStatus,
  tokenExpiresAt,
  connectionStatus,
  isConfigured,
  isConnecting = false,
  onClick,
  disabled = false,
  premiumBlocked = false,
  className,
  isUnpublished = false,
  requiresApiKey = false,
}: ToolCardProps) {
  const currentTime = useLiveTime();
  const isToolConfigured =
    connectionStatus !== undefined
      ? connectionStatus !== ConnectionStatus.NOT_CONNECTED
      : isConfigured;

  const getStatusConfig = () => {
    const actionText =
      requiresApiKey && !isToolConfigured
        ? "Configure API Key"
        : isToolConfigured
          ? "Edit Configuration"
          : "Connect";

    // Check if token is locally expired
    const isTokenExpired =
      tokenExpiresAt && tokenExpiresAt * 1000 < currentTime;

    switch (connectionStatus) {
      case ConnectionStatus.CONNECTED_NO_AUTH:
        return {
          label: "Connected",
          icon: ShieldCheck,
          iconColor: "text-green-700 dark:text-green-300",
          badgeVariant: "default" as const,
          bgColor: "bg-green-50 dark:bg-green-950/20",
          borderColor: "border-green-200 dark:border-green-800",
          badgeBg:
            "bg-white dark:bg-gray-800 border border-green-200 dark:border-green-700",
          badgeText: "text-green-700 dark:text-green-300",
          iconBoxBg:
            "bg-white dark:bg-gray-800 border border-green-200 dark:border-green-700",
          actionText,
        };
      case ConnectionStatus.CONNECTED_AUTH_VALID:
        // If token is expired, show as expired instead of authenticated
        if (isTokenExpired) {
          return {
            label: "Authentication expired",
            icon: XCircle,
            iconColor: "text-red-700 dark:text-red-300",
            badgeVariant: "secondary" as const,
            bgColor: "bg-red-50 dark:bg-red-950/20",
            borderColor: "border-red-200 dark:border-red-800",
            badgeBg:
              "bg-white dark:bg-gray-800 border border-red-200 dark:border-red-700",
            badgeText: "text-red-700 dark:text-red-300",
            iconBoxBg:
              "bg-white dark:bg-gray-800 border border-red-200 dark:border-red-700",
            actionText,
          };
        }
        return {
          label: "Authenticated",
          icon: ShieldCheck,
          iconColor: "text-green-700 dark:text-green-300",
          badgeVariant: "default" as const,
          bgColor: "bg-green-50 dark:bg-green-950/20",
          borderColor: "border-green-200 dark:border-green-800",
          badgeBg:
            "bg-white dark:bg-gray-800 border border-green-200 dark:border-green-700",
          badgeText: "text-green-700 dark:text-green-300",
          iconBoxBg:
            "bg-white dark:bg-gray-800 border border-green-200 dark:border-green-700",
          actionText,
        };
      case ConnectionStatus.CONNECTED_AUTH_INVALID:
        return {
          label: "Authentication required",
          icon: XCircle,
          iconColor: "text-red-700 dark:text-red-300",
          badgeVariant: "secondary" as const,
          bgColor: "bg-red-50 dark:bg-red-950/20",
          borderColor: "border-red-200 dark:border-red-800",
          badgeBg:
            "bg-white dark:bg-gray-800 border border-red-200 dark:border-red-700",
          badgeText: "text-red-700 dark:text-red-300",
          iconBoxBg:
            "bg-white dark:bg-gray-800 border border-red-200 dark:border-red-700",
          actionText,
        };
      case ConnectionStatus.CONFIGURATION_REQUIRED:
        return {
          label: "Configuration required",
          icon: XCircle,
          iconColor: "text-red-700 dark:text-red-300",
          badgeVariant: "secondary" as const,
          bgColor: "bg-red-50 dark:bg-red-950/20",
          borderColor: "border-red-200 dark:border-red-800",
          badgeBg:
            "bg-white dark:bg-gray-800 border border-red-200 dark:border-red-700",
          badgeText: "text-red-700 dark:text-red-300",
          iconBoxBg:
            "bg-white dark:bg-gray-800 border border-red-200 dark:border-red-700",
          actionText,
        };
      case ConnectionStatus.NOT_CONNECTED:
      default:
        return {
          label: "Not connected",
          icon: Wrench,
          iconColor: "text-muted-foreground",
          badgeVariant: "secondary" as const,
          bgColor: "",
          borderColor: "border-border",
          badgeBg:
            "bg-white dark:bg-gray-800 border border-muted-foreground/20",
          badgeText: "text-muted-foreground",
          iconBoxBg:
            "bg-white dark:bg-gray-800 border border-muted-foreground/20",
          actionText,
        };
    }
  };

  const statusConfig = getStatusConfig();
  const StatusIcon = statusConfig.icon;
  const timeLeft = formatTimeUntilExpiry(tokenExpiresAt, currentTime);

  return (
    <Card
      className={cn(
        "group overflow-hidden border transition-all hover:shadow-md",
        statusConfig.bgColor,
        statusConfig.borderColor,
        disabled && "opacity-50 cursor-not-allowed",
        className,
      )}
    >
      <div className="p-4">
        <div className="flex items-start gap-3 mb-3">
          <div className={cn("p-2.5 rounded-lg", statusConfig.iconBoxBg)}>
            <Wrench className="h-4 w-4" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-1.5 mb-1">
              <h4 className="font-semibold text-sm">
                {tool.name.replace(/_/g, " ")}
              </h4>
              {tool.tool_source === "mcp" && (
                <Badge
                  variant="outline"
                  className="h-4 text-[9px] px-1 gap-0.5 shrink-0"
                >
                  <Server className="h-2.5 w-2.5" />
                  MCP
                </Badge>
              )}
              {tool.is_premium && (
                <Badge
                  variant="outline"
                  className="h-4 text-[9px] px-1 gap-0.5 shrink-0 border-purple-300 text-purple-700 bg-purple-50 dark:border-purple-700 dark:text-purple-300 dark:bg-purple-950/40"
                >
                  <Crown className="h-2.5 w-2.5" />
                  Premium
                </Badge>
              )}
              {isUnpublished && (
                <Badge
                  variant="outline"
                  className="h-4 text-[9px] px-1 gap-0.5 shrink-0 border-amber-300 text-amber-700 bg-amber-50 dark:border-amber-700 dark:text-amber-300 dark:bg-amber-950/40"
                >
                  <EyeOff className="h-2.5 w-2.5" />
                  Unpublished
                </Badge>
              )}
            </div>
            <ExpandableDescription
              description={tool.description}
              descriptionId={`tool-card-description-${tool.id}`}
              textClassName="text-xs text-muted-foreground"
            />
            {tool.tool_source === "mcp" && tool.mcp_server_url && (
              <p
                className="text-[10px] text-muted-foreground/70 mt-1 truncate font-mono"
                title={tool.mcp_server_url}
              >
                {tool.mcp_server_url}
              </p>
            )}
            {tool.tool_source === "mcp" && (
              <p className="text-[10px] text-muted-foreground/80 mt-1">
                {tool.tool_functions_schema?.functions?.length
                  ? `${tool.tool_functions_schema.functions.length} exposed function${tool.tool_functions_schema.functions.length === 1 ? "" : "s"}`
                  : "Function catalog pending admin discovery"}
              </p>
            )}
            {isUnpublished && (
              <p className="text-[10px] text-amber-700 dark:text-amber-300 mt-1 flex items-center gap-1">
                <EyeOff className="h-3 w-3 shrink-0" />
                No longer in the catalog — still mapped to this agent.
              </p>
            )}
            {requiresApiKey && !isToolConfigured && (
              <p className="text-[10px] text-amber-700 dark:text-amber-300 mt-1 flex items-center gap-1">
                <Lock className="h-3 w-3 shrink-0" />
                API key required before connecting
              </p>
            )}
          </div>
        </div>

        <div className="flex items-center justify-between">
          <Badge
            variant={statusConfig.badgeVariant}
            className={cn(
              "flex items-center gap-1.5",
              statusConfig.badgeBg,
              statusConfig.badgeText,
            )}
          >
            <StatusIcon className={cn("h-3 w-3", statusConfig.iconColor)} />
            {statusConfig.label}
          </Badge>

          {premiumBlocked && tool.is_premium ? (
            <Button
              size="sm"
              variant="outline"
              onClick={onClick}
              disabled={isConnecting}
              className="shrink-0"
              title="Upgrade your plan to connect premium tools"
            >
              <Lock className="h-3 w-3 mr-1" />
              Premium
            </Button>
          ) : (
            <Button
              size="sm"
              variant={isConfigured || requiresApiKey ? "outline" : "default"}
              onClick={onClick}
              disabled={disabled || isConnecting}
              className="shrink-0"
            >
              {isConnecting ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                statusConfig.actionText
              )}
            </Button>
          )}
        </div>

        {authStatus === AuthStatus.AUTHENTICATED && timeLeft && (
          <div className="flex items-center gap-1.5 mt-3 text-xs text-muted-foreground">
            <Clock className="h-3 w-3" />
            <span>
              {timeLeft === "Expired" ? "Expired" : `Expires in ${timeLeft}`}
            </span>
          </div>
        )}
      </div>
    </Card>
  );
}
