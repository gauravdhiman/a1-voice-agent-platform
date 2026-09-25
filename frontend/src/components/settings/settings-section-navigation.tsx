import Link from "next/link";
import type { LucideIcon } from "lucide-react";

import { cn } from "@/lib/utils";

export interface SettingsNavigationSection {
  /** Stable identifier used by the URL and selected state. */
  id: string;
  /** Short section label shown in the settings navigation. */
  label: string;
  /** Explains which settings belong to this section. */
  description: string;
  /** Icon that helps distinguish the section at a glance. */
  icon: LucideIcon;
}

interface SettingsSectionNavigationProps {
  /** Accessible label for this group of settings links. */
  ariaLabel: string;
  /** Sections available in the current settings hub. */
  sections: readonly SettingsNavigationSection[];
  /** Identifier of the currently selected section. */
  activeSection: string;
  /** Builds the deep link for a selected section. */
  hrefForSection: (sectionId: string) => string;
}

/**
 * Render responsive section navigation for a settings hub.
 *
 * Links preserve the selected section in the URL, so each settings area can be
 * bookmarked and shared with an administrator who has access to that scope.
 */
export function SettingsSectionNavigation({
  ariaLabel,
  sections,
  activeSection,
  hrefForSection,
}: SettingsSectionNavigationProps) {
  return (
    <nav
      aria-label={ariaLabel}
      className="w-full md:w-56 md:shrink-0"
      data-testid="settings-section-navigation"
    >
      <div className="flex gap-2 overflow-x-auto pb-1 md:flex-col md:overflow-visible md:pb-0">
        {sections.map((section) => {
          const isActive = section.id === activeSection;
          const Icon = section.icon;

          return (
            <Link
              key={section.id}
              href={hrefForSection(section.id)}
              aria-current={isActive ? "page" : undefined}
              className={cn(
                "flex min-w-40 shrink-0 items-start gap-3 rounded-lg border px-3 py-2.5 text-left transition-colors md:w-full",
                isActive
                  ? "border-primary/25 bg-primary/5 text-foreground"
                  : "border-transparent text-muted-foreground hover:bg-muted hover:text-foreground",
              )}
            >
              <Icon
                aria-hidden="true"
                className={cn(
                  "mt-0.5 size-4 shrink-0",
                  isActive ? "text-primary" : "text-muted-foreground",
                )}
              />
              <span className="min-w-0">
                <span className="block text-sm font-medium">
                  {section.label}
                </span>
                <span className="mt-0.5 hidden text-xs leading-5 text-muted-foreground md:block">
                  {section.description}
                </span>
              </span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
