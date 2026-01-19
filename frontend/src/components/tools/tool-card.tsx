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
} from "lucide-react";
import { AuthStatus, ConnectionStatus } from "@/types/agent";
import { useLiveTime, formatTimeUntilExpiry } from "@/hooks/use-live-time";

export interface ToolCardProps {
  tool: {
    id: string;
    name: string;
    description: string | null;
  };
  authStatus: AuthStatus;
  tokenExpiresAt: number | null;
  connectionStatus?: ConnectionStatus;
  isConfigured?: boolean;
  isConnecting?: boolean;
  onClick: () => void;
  disabled?: boolean;
  className?: string;
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
  className,
}: ToolCardProps) {
  const currentTime = useLiveTime();

  const getStatusConfig = () => {
    const isToolConfigured =
      connectionStatus !== undefined
        ? connectionStatus !== ConnectionStatus.NOT_CONNECTED
        : isConfigured;
    const actionText = isToolConfigured ? "Edit Configuration" : "Connect";

    // Check if token is locally expired
    const isTokenExpired = tokenExpiresAt && (tokenExpiresAt * 1000) < currentTime;

    switch (connectionStatus) {
      case ConnectionStatus.CONNECTED_NO_AUTH:
        return {
          label: "Connected",
          icon: ShieldCheck,
          iconColor: "text-green-700 dark:text-green-300",
          badgeVariant: "default" as const,
          bgColor: "bg-green-50 dark:bg-green-950/20",
          borderColor: "border-green-200 dark:border-green-800",
          badgeBg: "bg-white dark:bg-gray-800 border border-green-200 dark:border-green-700",
          badgeText: "text-green-700 dark:text-green-300",
          iconBoxBg: "bg-white dark:bg-gray-800 border border-green-200 dark:border-green-700",
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
            badgeBg: "bg-white dark:bg-gray-800 border border-red-200 dark:border-red-700",
            badgeText: "text-red-700 dark:text-red-300",
            iconBoxBg: "bg-white dark:bg-gray-800 border border-red-200 dark:border-red-700",
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
          badgeBg: "bg-white dark:bg-gray-800 border border-green-200 dark:border-green-700",
          badgeText: "text-green-700 dark:text-green-300",
          iconBoxBg: "bg-white dark:bg-gray-800 border border-green-200 dark:border-green-700",
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
          badgeBg: "bg-white dark:bg-gray-800 border border-red-200 dark:border-red-700",
          badgeText: "text-red-700 dark:text-red-300",
          iconBoxBg: "bg-white dark:bg-gray-800 border border-red-200 dark:border-red-700",
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
          badgeBg: "bg-white dark:bg-gray-800 border border-muted-foreground/20",
          badgeText: "text-muted-foreground",
          iconBoxBg: "bg-white dark:bg-gray-800 border border-muted-foreground/20",
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
            <h4 className="font-semibold text-sm mb-1">
              {tool.name.replace(/_/g, " ")}
            </h4>
            <p className="text-xs text-muted-foreground line-clamp-2">
              {tool.description}
            </p>
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

          <Button
            size="sm"
            variant={isConfigured ? "outline" : "default"}
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
