"use client";

import { AlertCircle } from "lucide-react";
import { cn } from "@/lib/utils";

interface StripeSyncAlertProps {
  title: string;
  message: string;
  className?: string;
}

/**
 * Inline alert when Stripe auto-sync failed and manual linking is required.
 */
export function StripeSyncAlert({ title, message, className }: StripeSyncAlertProps) {
  return (
    <div
      className={cn(
        "rounded-md border border-amber-500/40 bg-amber-500/10 px-3 py-2.5 text-sm",
        className,
      )}
      role="alert"
    >
      <div className="flex gap-2">
        <AlertCircle className="h-4 w-4 shrink-0 text-amber-600 mt-0.5" />
        <div className="space-y-1">
          <p className="font-medium text-foreground">{title}</p>
          <p className="text-muted-foreground text-xs leading-relaxed">{message}</p>
        </div>
      </div>
    </div>
  );
}
