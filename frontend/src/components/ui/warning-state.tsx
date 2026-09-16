import React from "react";
import { AlertTriangle, ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface WarningStateProps {
  title?: string;
  message?: string;
  onAction?: () => void;
  actionLabel?: string;
  variant?: "default" | "minimal";
  className?: string;
}

export function WarningState({
  title = "Warning",
  message = "Please check the information and try again.",
  onAction,
  actionLabel = "Go back",
  variant = "default",
  className,
}: WarningStateProps) {
  if (variant === "minimal") {
    return (
      <div className={cn("flex items-center justify-center h-64", className)}>
        <div className="flex flex-col items-center space-y-2 text-center">
          <AlertTriangle className="h-6 w-6 status-text-warning" />
          <div className="status-text-warning text-sm">{message}</div>
          {onAction && (
            <Button
              variant="outline"
              size="sm"
              onClick={onAction}
              className="mt-2"
            >
              <ArrowLeft className="h-4 w-4 mr-2" />
              {actionLabel}
            </Button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className={cn("p-6", className)}>
      <Card className="status-callout warning">
        <CardContent className="p-6">
          <div className="flex flex-col items-center text-center space-y-4">
            <div className="status-icon-surface warning rounded-full p-3">
              <AlertTriangle className="h-8 w-8 status-text-warning" />
            </div>
            <div className="space-y-2">
              <h3 className="text-lg font-semibold status-text-warning">
                {title}
              </h3>
              <p className="text-sm status-text-warning max-w-md">{message}</p>
            </div>
            {onAction && (
              <Button onClick={onAction} variant="outline">
                <ArrowLeft className="h-4 w-4 mr-2" />
                {actionLabel}
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
