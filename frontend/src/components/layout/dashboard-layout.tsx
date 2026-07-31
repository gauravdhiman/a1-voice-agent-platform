"use client";

import React, { useState } from "react";
import { useRouter, usePathname, useSearchParams } from "next/navigation";
import { useAuth } from "@/contexts/auth-context";
import { useOrganization } from "@/contexts/organization-context";
import {
  Building2,
  Settings,
  ChevronLeft,
  ChevronRight,
  LogOut,
  Users,
  CreditCard,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuItemLink,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
  DropdownMenuLabel,
} from "@/components/ui/dropdown-menu";
import { ThemeToggle } from "@/components/ui/theme-toggle";
import { NavigationLink } from "@/components/ui/navigation-link";
import { OrganizationSwitcher } from "@/components/layout/organization-switcher";
import {
  ALL_NAV_ITEMS,
  NAV_SECTIONS,
  SECTION_ROLES,
  type NavItem,
  type NavSection,
} from "@/components/layout/nav-config";
import { useHasPermission } from "@/hooks/use-has-permission";
import { useUserPermissions } from "@/hooks/use-user-permissions";

interface DashboardLayoutProps {
  children: React.ReactNode;
}

/**
 * Human-readable heading for each nav section. Hidden when the section
 * is empty (no items visible to the current user).
 */
const SECTION_LABELS: Readonly<Record<NavSection, string>> = {
  workspace: "Workspace",
  org_admin: "Org Admin",
  platform_admin: "Platform Admin",
};

export function DashboardLayout({ children }: DashboardLayoutProps) {
  const { user, signOut } = useAuth();
  const { organizations, currentOrganization } = useOrganization();
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  const handleSignOut = async () => {
    const { error } = await signOut();
    if (error) {
      console.error("Error signing out:", error);
    } else {
      router.push("/auth/signin");
    }
  };

  // Check if user is a platform admin (for the avatar-dropdown org links).
  const isPlatformAdmin = user?.hasRole("platform_admin");

  // Resolve the current org role. Platform admins trump everything;
  // otherwise the user has a per-org role on the current org.
  const currentOrganizationRole = isPlatformAdmin
    ? "platform_admin"
    : currentOrganization && user
      ? user.hasRole("org_admin", currentOrganization.id)
        ? "org_admin"
        : "member"
      : null;

  const getInitials = (name: string) => {
    return name
      .split(" ")
      .map((n) => n[0])
      .join("")
      .toUpperCase()
      .slice(0, 2);
  };

  const getBreadcrumbs = () => {
    const breadcrumbs = [];
    const orgId = searchParams.get("org_id");

    if (pathname === "/dashboard") {
      breadcrumbs.push({ name: "Dashboard", href: null });
    } else if (pathname === "/organizations") {
      breadcrumbs.push({ name: "Organizations", href: null });
    } else if (pathname === "/organization") {
      breadcrumbs.push({ name: "Organization", href: null });
    } else if (pathname === "/organization/members") {
      const orgHref = orgId ? `/organization?org_id=${orgId}` : "/organization";
      breadcrumbs.push({ name: "Organization", href: orgHref });
      breadcrumbs.push({ name: "Members", href: null });
    } else if (pathname === "/agents") {
      breadcrumbs.push({ name: "Agents", href: null });
    } else if (
      pathname.startsWith("/agents/") &&
      pathname.split("/").length === 3
    ) {
      breadcrumbs.push({ name: "Agents", href: "/agents" });
      breadcrumbs.push({ name: "Agent Details", href: null });
    } else if (pathname.startsWith("/phone-numbers")) {
      breadcrumbs.push({ name: "Phone Numbers", href: null });
    } else if (pathname.startsWith("/skills")) {
      breadcrumbs.push({ name: "Skills", href: null });
    } else if (pathname === "/users") {
      if (isPlatformAdmin) {
        breadcrumbs.push({ name: "Users", href: null });
      } else {
        breadcrumbs.push({ name: "Dashboard", href: null });
      }
    } else if (pathname === "/platform/skills") {
      if (isPlatformAdmin) {
        breadcrumbs.push({ name: "Platform Skills", href: null });
      } else {
        breadcrumbs.push({ name: "Dashboard", href: null });
      }
    } else if (pathname === "/platform/tools") {
      // Mirror /platform/skills: platform admins see the route's own title;
      // anyone else (e.g. a regular member who somehow lands here) sees the
      // generic "Dashboard" fallback. The page itself independently gates on
      // the platform_admin role via <AccessDenied>.
      if (isPlatformAdmin) {
        breadcrumbs.push({ name: "Platform Tools", href: null });
      } else {
        breadcrumbs.push({ name: "Dashboard", href: null });
      }
    } else if (pathname === "/platform/presets") {
      // Mirror /platform/tools: platform admins see the route's own title;
      // anyone else sees the generic "Dashboard" fallback. The page itself
      // independently gates on the platform_admin role via <AccessDenied>.
      if (isPlatformAdmin) {
        breadcrumbs.push({ name: "Voice Presets", href: null });
      } else {
        breadcrumbs.push({ name: "Dashboard", href: null });
      }
    } else if (pathname === "/organization/billing") {
      const orgHref = orgId ? `/organization?org_id=${orgId}` : "/organization";
      breadcrumbs.push({ name: "Organization", href: orgHref });
      breadcrumbs.push({ name: "Billing", href: null });
    } else if (pathname === "/settings") {
      breadcrumbs.push({ name: "Settings", href: null });
    } else if (pathname.startsWith("/organization")) {
      const orgHref = orgId ? `/organization?org_id=${orgId}` : "/organization";
      if (pathname.includes("/members")) {
        breadcrumbs.push({ name: "Organization", href: orgHref });
        breadcrumbs.push({ name: "Members", href: null });
      } else {
        breadcrumbs.push({ name: "Organization", href: null });
      }
    } else {
      breadcrumbs.push({ name: "Dashboard", href: null });
    }

    return breadcrumbs;
  };

  return (
    <div className="h-screen bg-background flex overflow-hidden font-sans">
      {/* Sidebar */}
      <aside
        className={`bg-sidebar border-r border-sidebar-border shadow-sm transition-all duration-300 ease-in-out ${
          sidebarCollapsed ? "w-16" : "w-64"
        } flex flex-col h-full z-20`}
      >
        {/* Sidebar Header */}
        <div className="h-14 flex items-center justify-between px-4 border-b border-sidebar-border bg-sidebar">
          {!sidebarCollapsed && (
            <div className="flex items-center space-x-2">
              <div className="bg-sidebar-primary w-7 h-7 rounded-md flex items-center justify-center">
                <span className="text-sidebar-primary-foreground font-bold text-base">
                  AI
                </span>
              </div>
              <span className="text-base font-bold text-sidebar-foreground tracking-tight">
                {process.env.NEXT_PUBLIC_APP_NAME ?? "CogniNets"}
              </span>
            </div>
          )}
          {sidebarCollapsed && (
            <div className="mx-auto bg-sidebar-primary w-7 h-7 rounded-md flex items-center justify-center">
              <span className="text-sidebar-primary-foreground font-bold text-base">
                AI
              </span>
            </div>
          )}
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
            className={`h-8 w-8 text-sidebar-foreground/50 hover:text-sidebar-foreground hover:bg-sidebar-accent ${
              sidebarCollapsed ? "hidden" : ""
            }`}
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
        </div>

        {/* Organization switcher (N1 redesign). Sits between the header
            and the nav so the current org context is the first thing the
            user sees. Hidden in the collapsed state to keep the rail
            minimal. */}
        {!sidebarCollapsed && (
          <div className="px-3 pt-3">
            <OrganizationSwitcher
              currentRole={currentOrganizationRole}
            />
          </div>
        )}

        {/* Navigation */}
        <div className="flex-1 py-4 px-3 space-y-1 overflow-y-auto">
          <NavSectionGroup
            section="workspace"
            items={NAV_SECTIONS.workspace}
            collapsed={sidebarCollapsed}
            pathname={pathname}
          />
          <NavSectionGroup
            section="org_admin"
            items={NAV_SECTIONS.org_admin}
            collapsed={sidebarCollapsed}
            pathname={pathname}
          />
          <NavSectionGroup
            section="platform_admin"
            items={NAV_SECTIONS.platform_admin}
            collapsed={sidebarCollapsed}
            pathname={pathname}
          />
        </div>

        {/* Sidebar Footer */}
        <div className="p-3 border-t border-sidebar-border bg-sidebar">
          <div
            className={`flex items-center ${
              sidebarCollapsed ? "justify-center" : "space-x-3"
            }`}
          >
            <Avatar className="h-8 w-8 border border-sidebar-border">
              <AvatarFallback className="bg-sidebar-primary/10 text-sidebar-primary font-medium text-xs">
                {user?.firstName
                  ? getInitials(`${user.firstName} ${user.lastName || ""}`)
                  : "U"}
              </AvatarFallback>
            </Avatar>
            {!sidebarCollapsed && (
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-sidebar-foreground truncate">
                  {user?.firstName} {user?.lastName}
                </p>
                <p className="text-xs text-sidebar-foreground/60 truncate">
                  {user?.email}
                </p>
              </div>
            )}
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col h-full overflow-hidden bg-muted/30">
        {/* Header */}
        <header className="h-14 bg-background border-b border-border shadow-sm flex items-center justify-between px-6 z-10">
          <div className="flex items-center">
            {sidebarCollapsed && (
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setSidebarCollapsed(false)}
                className="mr-4 h-8 w-8 text-muted-foreground hover:text-foreground"
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            )}

            {/* Breadcrumbs */}
            <nav className="hidden md:flex" aria-label="Breadcrumb">
              <ol className="inline-flex items-center space-x-1 md:space-x-2">
                {getBreadcrumbs().map((breadcrumb, index) => (
                  <li key={index} className="inline-flex items-center">
                    {index > 0 && (
                      <ChevronRight className="w-3.5 h-3.5 text-muted-foreground mx-1" />
                    )}
                    {breadcrumb.href ? (
                      <NavigationLink
                        href={breadcrumb.href!}
                        className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors px-0 py-0 space-x-0 w-auto"
                        baseClassName=""
                        activeClassName=""
                        exact
                      >
                        {breadcrumb.name}
                      </NavigationLink>
                    ) : (
                      <span className="text-sm font-semibold text-foreground">
                        {breadcrumb.name}
                      </span>
                    )}
                  </li>
                ))}
              </ol>
            </nav>
          </div>

          <div className="flex items-center space-x-4">
            <ThemeToggle />

            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="ghost"
                  className="relative h-8 w-8 rounded-full p-0 ring-2 ring-transparent hover:ring-primary/20 transition-all"
                >
                  <Avatar className="h-8 w-8">
                    <AvatarFallback className="bg-primary text-primary-foreground font-medium text-xs">
                      {user?.firstName
                        ? getInitials(
                            `${user.firstName} ${user.lastName || ""}`,
                          )
                        : "U"}
                    </AvatarFallback>
                  </Avatar>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56 p-2">
                <DropdownMenuLabel className="font-normal">
                  <div className="flex flex-col space-y-1">
                    <p className="text-sm font-medium leading-none">
                      {user?.firstName} {user?.lastName}
                    </p>
                    <p className="text-xs leading-none text-muted-foreground">
                      {user?.email}
                    </p>
                  </div>
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItemLink href="/settings">
                  <Settings className="mr-2 h-4 w-4" />
                  <span>Settings</span>
                </DropdownMenuItemLink>
                {/* N1 Epic D: org admin links (Members / Billing /
                    Organization) live in the left-nav only. The avatar
                    menu no longer duplicates them. Multi-org users still
                    get a "Switch Org" shortcut to /organizations. */}
                {organizations.length > 1 && (
                  <>
                    <DropdownMenuSeparator />
                    <DropdownMenuItemLink href="/organizations">
                      <Building2 className="mr-2 h-4 w-4" />
                      <span>Switch Org</span>
                    </DropdownMenuItemLink>
                  </>
                )}
                <DropdownMenuSeparator />
                <DropdownMenuItem
                  onClick={handleSignOut}
                  className="text-destructive focus:text-destructive cursor-pointer"
                >
                  <LogOut className="mr-2 h-4 w-4" />
                  <span>Sign out</span>
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 overflow-y-auto p-4">
          <div className="max-w-6xl mx-auto">{children}</div>
        </main>
      </div>
    </div>
  );
}

/**
 * Renders one nav section. The section heading is hidden when the
 * section is empty (no items visible to the current user) OR when
 * the user lacks the section's required role (see `SECTION_ROLES` in
 * `nav-config.ts`).
 *
 * The hook `useHasPermission` is called per-item via a sub-component so
 * that React Hooks ordering stays consistent regardless of how many items
 * the section has. Each `<NavSectionItem>` mounts only if its item passes
 * the permission filter; that means the hook is conditional on the
 * caller's decision, not the filter's outcome.
 */
function NavSectionGroup({
  section,
  items,
  collapsed,
  pathname,
}: {
  section: NavSection;
  items: readonly NavItem[];
  collapsed: boolean;
  pathname: string;
}) {
  // Section-level role gate (Option C). A user with the underlying
  // permissions but not the required role must not see the section
  // heading or the items inside it — otherwise the nav would promise
  // what the page denies (e.g. an org_admin holding `member:read`
  // would see "Members" but be denied on /organization/members).
  const requiredRole = SECTION_ROLES[section];
  const { isPlatformAdmin, isOrgAdmin } = useUserPermissions();
  const hasRequiredRole =
    requiredRole === null
      ? true
      : requiredRole === "platform_admin"
        ? isPlatformAdmin
        : // org_admin section: platform_admin inherits the role
          isOrgAdmin || isPlatformAdmin;

  if (!hasRequiredRole) return null;

  return (
    <div data-testid={`nav-section-${section}`} className="space-y-1">
      {!collapsed && (
        <div
          className="px-2 pt-3 pb-1 text-[10px] font-semibold uppercase tracking-wider text-sidebar-foreground/50"
          aria-hidden
        >
          {SECTION_LABELS[section]}
        </div>
      )}
      {items.map((item) => (
        <NavSectionItem
          key={item.name}
          item={item}
          collapsed={collapsed}
          pathname={pathname}
        />
      ))}
    </div>
  );
}

function NavSectionItem({
  item,
  collapsed,
  pathname,
}: {
  item: NavItem;
  collapsed: boolean;
  pathname: string;
}) {
  // `useHasPermission` returns `null` while loading; we treat that as
  // "not visible" so the user never sees items they don't actually have
  // permission for. (Loading state is rare because the /me query is
  // warmed at app boot.)
  const visible = useHasPermission(item.requiredPermission);
  if (!visible) return null;

  const Icon = item.icon;
  const isActive =
    pathname === item.href ||
    (!item.exact && pathname.startsWith(`${item.href}/`));

  return (
    <NavigationLink
      href={item.href}
      title={collapsed ? item.name : undefined}
      exact={item.exact ?? true}
      className={collapsed ? "justify-center" : ""}
    >
      <Icon
        className={`h-4 w-4 flex-shrink-0 ${
          isActive
            ? "text-sidebar-primary"
            : "text-sidebar-foreground/50 group-hover:text-sidebar-foreground"
        }`}
      />
      {!collapsed && <span>{item.name}</span>}
      {collapsed && isActive && (
        <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-6 bg-sidebar-primary rounded-r-full" />
      )}
    </NavigationLink>
  );
}

// `ALL_NAV_ITEMS` re-exported for tests that need to assert the full
// configured set without depending on the layout's render order.
export { ALL_NAV_ITEMS };
