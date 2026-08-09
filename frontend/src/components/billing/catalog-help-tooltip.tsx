"use client";

import * as React from "react";
import { CircleHelp } from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

interface CatalogHelpTooltipProps {
  /** Help text shown on hover/focus. */
  content: string;
  /** Optional accessible label override. */
  label?: string;
}

/**
 * Info icon with tooltip for plan and entitlement catalog admin fields.
 */
export function CatalogHelpTooltip({ content, label }: CatalogHelpTooltipProps) {
  return (
    <TooltipProvider delayDuration={300}>
      <Tooltip disableHoverableContent>
        <TooltipTrigger asChild>
          <button
            type="button"
            tabIndex={-1}
            className="inline-flex text-muted-foreground hover:text-foreground focus:outline-none"
            aria-label={label ?? "More information"}
          >
            <CircleHelp className="h-4 w-4" />
          </button>
        </TooltipTrigger>
        <TooltipContent className="max-w-sm text-sm leading-relaxed">
          {content}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

interface CatalogFieldLabelProps {
  htmlFor?: string;
  children: React.ReactNode;
  help?: string;
}

/**
 * Label row with optional help tooltip for catalog forms.
 */
export function CatalogFieldLabel({
  htmlFor,
  children,
  help,
}: CatalogFieldLabelProps) {
  return (
    <div className="flex items-center gap-1.5">
      <label htmlFor={htmlFor} className="text-sm font-medium leading-none">
        {children}
      </label>
      {help ? <CatalogHelpTooltip content={help} label={`Help: ${children}`} /> : null}
    </div>
  );
}
