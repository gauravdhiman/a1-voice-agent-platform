/**
 * OrganizationSwitcher — sidebar widget for picking the current org.
 *
 * The current org is the first thing a user sees in the workspace
 * (N1 redesign). The widget shows the current org's name and role
 * badge in a button that opens a popover listing every org the user
 * belongs to. A "Create organization" entry at the bottom of the
 * popover links to the create-organization flow.
 *
 * The popover also marks the **active** row (the currently selected
 * org) without offering a "Switch" action — you cannot switch to the
 * org you're already on.
 *
 * The widget hides itself entirely when the user has no current org
 * (e.g. a freshly signed-in user with no orgs yet); the avatar
 * dropdown still surfaces org-related entries.
 */
"use client";

import * as React from "react";
import Link from "next/link";
import { Building2, Check, ChevronsUpDown, Plus } from "lucide-react";
import { useOrganization } from "@/contexts/organization-context";
import { Button } from "@/components/ui/button";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { cn } from "@/lib/utils";
import type { Organization } from "@/types/organization";

/** Human-readable role labels used in the switcher badge. */
const ROLE_LABELS: Readonly<Record<string, string>> = {
  platform_admin: "Platform admin",
  org_admin: "Org admin",
  member: "Member",
};

interface OrganizationSwitcherProps {
  /**
   * The current user's role on the current org. Used to render the
   * role badge in the trigger and the popover. Optional: when omitted,
   * no badge is shown.
   */
  currentRole?: string | null;
}

/**
 * Format a role key like `org_admin` into `Org admin`. Returns the key
 * itself when there's no mapping.
 */
function formatRole(role: string | null | undefined): string {
  if (!role) return "Member";
  return ROLE_LABELS[role] ?? role;
}

export function OrganizationSwitcher({
  currentRole,
}: OrganizationSwitcherProps) {
  const { organizations, currentOrganization, setCurrentOrganization } =
    useOrganization();

  if (!currentOrganization) {
    // No current org -> nothing to switch to. The avatar dropdown
    // handles the "create your first org" affordance.
    return null;
  }

  const handleSwitch = (org: Organization) => {
    setCurrentOrganization(org);
  };

  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          aria-label="Switch organization"
          className="w-full justify-between px-3"
        >
          <span className="flex items-center gap-2 min-w-0">
            <Building2 className="h-4 w-4 text-sidebar-foreground/60 flex-shrink-0" />
            <span className="font-medium text-sm truncate">
              {currentOrganization.name}
            </span>
            {currentRole ? (
              <span className="ml-1 inline-flex items-center rounded-full bg-sidebar-primary/10 px-2 py-0.5 text-[10px] font-semibold text-sidebar-primary">
                {formatRole(currentRole)}
              </span>
            ) : null}
          </span>
          <ChevronsUpDown className="h-3.5 w-3.5 text-sidebar-foreground/50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-72 p-2" align="start">
        <div className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground px-2 pt-1 pb-2">
          Switch organization
        </div>
        <ul className="space-y-1">
          {organizations.map((org) => {
            const isActive = org.id === currentOrganization.id;
            return (
              <li
                key={org.id}
                data-row
                data-active={isActive ? "true" : undefined}
                className={cn(
                  "flex items-center justify-between gap-2 rounded-md px-2 py-1.5 text-sm",
                  isActive
                    ? "bg-sidebar-primary/10"
                    : "hover:bg-muted/50",
                )}
              >
                <span className="flex items-center gap-2 min-w-0">
                  <Building2 className="h-3.5 w-3.5 text-muted-foreground flex-shrink-0" />
                  <span className="truncate">{org.name}</span>
                  {isActive ? (
                    <Check
                      className="h-3.5 w-3.5 text-sidebar-primary flex-shrink-0"
                      aria-label="Current"
                    />
                  ) : null}
                </span>
                {isActive ? (
                  <span className="text-[10px] font-semibold uppercase text-sidebar-primary">
                    Current
                  </span>
                ) : (
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => handleSwitch(org)}
                    className="h-6 px-2 text-xs"
                  >
                    Switch
                  </Button>
                )}
              </li>
            );
          })}
        </ul>
        <div className="mt-2 pt-2 border-t border-border">
          <Link
            href="/auth/create-organization"
            className="flex items-center gap-2 rounded-md px-2 py-1.5 text-sm text-muted-foreground hover:bg-muted/50 hover:text-foreground"
          >
            <Plus className="h-3.5 w-3.5" />
            <span>Create organization</span>
          </Link>
        </div>
      </PopoverContent>
    </Popover>
  );
}
