import * as React from "react";
import { cn } from "@/lib/utils";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Wrench, ShieldCheck, AlertCircle, Clock } from "lucide-react";
import { AuthStatus } from "@/types/agent";

export interface ToolCardProps {
  tool: {
    id: string;
    name: string;
    description: string | null;
  };
  authStatus: AuthStatus;
  isEnabled: boolean;
  tokenExpiresAt: number | null;
  onClick: () => void;
  disabled?: boolean;
  className?: string;
}

export function ToolCard({
  tool,
  authStatus,
  isEnabled,
  tokenExpiresAt,
  onClick,
  disabled = false,
  className,
}: ToolCardProps) {
  const getTimeUntilExpiry = (expiresAt: number | null) => {
    if (!expiresAt) return null;
    const secondsLeft = Math.floor((expiresAt * 1000 - Date.now()) / 1000);
    const minutesLeft = Math.floor(secondsLeft / 60);

    if (minutesLeft < 1) return "< 1 minute";
    if (minutesLeft < 60) return `${minutesLeft} minutes`;
    if (minutesLeft < 1440) return `${Math.floor(minutesLeft / 60)} hours`;
    return `${Math.floor(minutesLeft / 1440)} days`;
  };

  const getStatusConfig = () => {
    switch (authStatus) {
      case AuthStatus.AUTHENTICATED:
        return {
          label: "Connected",
          icon: ShieldCheck,
          iconColor: "text-green-500",
          badgeVariant: "default" as const,
          bgColor: "bg-green-500",
          actionText: "Configure",
        };
      case AuthStatus.EXPIRED:
        return {
          label: "Expired",
          icon: AlertCircle,
          iconColor: "text-orange-500",
          badgeVariant: "secondary" as const,
          bgColor: "bg-orange-500",
          actionText: "Connect",
        };
      case AuthStatus.NOT_AUTHENTICATED:
      default:
        return {
          label: "Not configured",
          icon: Wrench,
          iconColor: "text-muted-foreground",
          badgeVariant: "secondary" as const,
          bgColor: "bg-muted",
          actionText: "Connect",
        };
    }
  };

  const statusConfig = getStatusConfig();
  const StatusIcon = statusConfig.icon;
  const timeLeft = getTimeUntilExpiry(tokenExpiresAt);

  return (
    <Card
      className={cn(
        "group overflow-hidden border transition-all hover:shadow-md",
        isEnabled ? "border-primary/20 bg-primary/5" : "border-muted/50",
        disabled && "opacity-50 cursor-not-allowed",
        className,
      )}
    >
      <div className="p-4">
        <div className="flex items-start gap-3 mb-3">
          <div
            className={cn(
              "p-2.5 rounded-lg",
              isEnabled ? "bg-primary" : "bg-muted",
            )}
          >
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
              authStatus === AuthStatus.AUTHENTICATED &&
                "bg-green-500/10 text-green-700 dark:text-green-400",
              authStatus === AuthStatus.EXPIRED &&
                "bg-orange-500/10 text-orange-700 dark:text-orange-400",
            )}
          >
            <StatusIcon className={cn("h-3 w-3", statusConfig.iconColor)} />
            {statusConfig.label}
          </Badge>

          <Button
            size="sm"
            variant={isEnabled ? "outline" : "default"}
            onClick={onClick}
            disabled={disabled}
            className="shrink-0"
          >
            {statusConfig.actionText}
          </Button>
        </div>

        {authStatus === AuthStatus.AUTHENTICATED && timeLeft && (
          <div className="flex items-center gap-1.5 mt-3 text-xs text-muted-foreground">
            <Clock className="h-3 w-3" />
            <span>Expires in {timeLeft}</span>
          </div>
        )}
      </div>
    </Card>
  );
}
