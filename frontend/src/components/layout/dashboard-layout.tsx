"use client";

import React, { useEffect, useState } from "react";
import { useRouter, usePathname, useSearchParams } from "next/navigation";
import { useAuth } from "@/contexts/auth-context";
import { useOrganization } from "@/contexts/organization-context";
import {
  CircleHelp,
  Settings,
  ChevronLeft,
  ChevronRight,
  Menu,
  X,
  LogOut,
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
import { SiteThemeSwitch } from "@/components/public-theme/theme-switch";
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
import { SITE_NAME } from "@/lib/site-config";
import { useProductTour } from "@/components/product-tour/product-tour-provider";

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
  const { currentOrganization } = useOrganization();
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const { openProductTour } = useProductTour();
  // Keep the server and first client render identical; the media query below
  // applies the mobile shell immediately after hydration without a mismatch.
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const mobile = window.matchMedia("(max-width: 767px)");
    const update = () => {
      setIsMobile(mobile.matches);
      setSidebarCollapsed(mobile.matches);
    };
    update();
    mobile.addEventListener("change", update);
    return () => mobile.removeEventListener("change", update);
  }, []);

  useEffect(() => {
    if (window.matchMedia("(max-width: 767px)").matches) {
      setSidebarCollapsed(true);
    }
  }, [pathname]);

  useEffect(() => {
    if (!isMobile || sidebarCollapsed) return;

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [isMobile, sidebarCollapsed]);

  // Sidebar brand. If the name ends in " AI" (e.g. "24x7 AI"), strip the
  // trailing " AI" from the wordmark so the "AI" logo chip below is not
  // duplicated next to the full name (which would read "AI 24x7 AI").
  const appName = SITE_NAME;
  const brandName = appName.replace(/\s+AI(?:\s+Platform)?$/, "");

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
      if (isPlatformAdmin) {
        breadcrumbs.push({ name: "Organizations", href: null });
      } else {
        breadcrumbs.push({ name: "Dashboard", href: null });
      }
    } else if (pathname === "/organizations/credits") {
      if (isPlatformAdmin) {
        breadcrumbs.push({ name: "Organizations", href: "/organizations" });
        breadcrumbs.push({ name: "Credits & entitlements", href: null });
      } else {
        breadcrumbs.push({ name: "Dashboard", href: null });
      }
    } else if (pathname === "/organization") {
      breadcrumbs.push({ name: "Organization", href: null });
    } else if (pathname === "/organization/members") {
      const orgHref = orgId ? `/organization?org_id=${orgId}` : "/organization";
      breadcrumbs.push({ name: "Organization", href: orgHref });
      breadcrumbs.push({ name: "Members", href: null });
    } else if (pathname.startsWith("/organization/tools")) {
      const orgHref = orgId ? `/organization?org_id=${orgId}` : "/organization";
      breadcrumbs.push({ name: "Organization", href: orgHref });
      breadcrumbs.push({ name: "Organization Tools", href: null });
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
    } else if (pathname === "/platform/templates") {
      if (isPlatformAdmin) {
        breadcrumbs.push({ name: "Use Case Templates", href: null });
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
    } else if (pathname === "/platform/phone-numbers") {
      if (isPlatformAdmin) {
        breadcrumbs.push({ name: "Phone Number Settings", href: null });
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
    <div className="dashboard-shell flex h-[100dvh] overflow-hidden bg-background font-sans">
      {!sidebarCollapsed && (
        <button
          aria-label="Dismiss navigation"
          onClick={() => setSidebarCollapsed(true)}
          className="fixed inset-0 z-40 bg-slate-950/35 backdrop-blur-[2px] transition-opacity md:hidden"
        />
      )}
      {/* Sidebar */}
      <aside
        data-testid="dashboard-sidebar"
        className={`bg-sidebar border-r border-sidebar-border shadow-sm transition-all duration-300 ease-in-out ${
          sidebarCollapsed
            ? "hidden md:flex md:w-16"
            : "fixed inset-y-0 right-0 z-50 w-[84vw] max-w-sm border-l border-r-0 shadow-2xl md:relative md:inset-y-auto md:right-auto md:z-auto md:w-64 md:border-l-0 md:border-r md:shadow-sm"
        } flex h-full shrink-0 flex-col`}
      >
        {/* Sidebar Header */}
        <div
          className="flex h-16 items-center justify-between border-b border-sidebar-border bg-sidebar px-4 sm:h-14"
          data-tour="brand"
        >
          {!sidebarCollapsed && (
            <div className="flex items-center gap-1.5">
              {/* Brand pill: a single continued box split into a lighter
                  "24x7" zone and a solid "AI" zone. No outer border: a stroke
                  would show around the light zone but merge into the solid
                  "AI" zone, making the two halves look different sizes. */}
              <div className="flex items-center overflow-hidden rounded-lg">
                <span className="bg-sidebar-primary/15 text-sidebar-primary font-bold text-sm tracking-tight px-2.5 py-1 whitespace-nowrap">
                  {brandName}
                </span>
                <span className="bg-sidebar-primary text-sidebar-primary-foreground font-bold text-sm px-2.5 py-1">
                  AI
                </span>
              </div>
              {/* Live dot: the AI front desk is always answering. Same
                  motif as the marketing hero's "live" badge. */}
              <span
                data-testid="brand-live-dot"
                className="relative flex h-2 w-2"
              >
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
              </span>
            </div>
          )}
          {sidebarCollapsed && (
            <div className="mx-auto flex items-center gap-1">
              <div className="bg-sidebar-primary w-7 h-7 rounded-md flex items-center justify-center">
                <span className="text-sidebar-primary-foreground font-bold text-base">
                  AI
                </span>
              </div>
              <span
                data-testid="brand-live-dot"
                className="relative flex h-2 w-2"
              >
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
              </span>
            </div>
          )}
          {!sidebarCollapsed && (
            <Button
              variant="ghost"
              size="icon"
              aria-label={isMobile ? "Close navigation" : "Collapse navigation"}
              onClick={() => setSidebarCollapsed(true)}
              className="h-9 w-9 text-sidebar-foreground/50 hover:bg-sidebar-accent hover:text-sidebar-foreground"
            >
              <X className="h-4 w-4 md:hidden" />
              <ChevronLeft className="hidden h-4 w-4 md:block" />
            </Button>
          )}
        </div>

        {/* Organization switcher (N1 redesign). Sits between the header
            and the nav so the current org context is the first thing the
            user sees. Hidden in the collapsed state to keep the rail
            minimal. */}
        {!sidebarCollapsed && (
          <div className="px-3 pt-3" data-tour="organization-switcher">
            <OrganizationSwitcher currentRole={currentOrganizationRole} />
          </div>
        )}

        {/* Navigation */}
        <div className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
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
        <div className="border-t border-sidebar-border bg-sidebar p-3 pb-[calc(0.75rem+env(safe-area-inset-bottom))]">
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
      <div className="flex h-full min-w-0 flex-1 flex-col overflow-hidden bg-muted/30">
        {/* Header */}
        <header className="sticky top-0 z-30 flex h-16 shrink-0 items-center justify-between border-b border-border bg-background/95 px-3 shadow-sm backdrop-blur sm:h-14 sm:px-5 lg:px-6">
          <div className="flex min-w-0 items-center gap-2">
            {sidebarCollapsed && !isMobile && (
              <Button
                variant="ghost"
                size="icon"
                aria-label="Expand navigation rail"
                aria-expanded={!sidebarCollapsed}
                onClick={() => setSidebarCollapsed(false)}
                className="hidden h-9 w-9 shrink-0 text-muted-foreground hover:text-foreground md:flex sm:mr-2"
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            )}

            {/* Breadcrumbs */}
            <nav className="hidden min-w-0 sm:flex" aria-label="Breadcrumb">
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
            <span className="truncate text-sm font-semibold text-foreground sm:hidden">
              {getBreadcrumbs().at(-1)?.name ?? "Dashboard"}
            </span>
          </div>

          <div
            className="flex shrink-0 items-center gap-1 sm:gap-2"
            data-testid="dashboard-header-actions"
          >
            <SiteThemeSwitch />
            <Button
              variant="ghost"
              size="icon"
              aria-label="Open product walkthrough"
              title="Open product walkthrough"
              onClick={openProductTour}
              className="h-8 w-8 text-muted-foreground hover:text-foreground"
            >
              <CircleHelp className="h-4 w-4" />
              <span className="sr-only">Open product walkthrough</span>
            </Button>

            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="ghost"
                  className="relative h-8 w-8 rounded-full p-0 ring-2 ring-transparent hover:ring-primary/20 transition-all"
                  data-tour="user-menu"
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
                {/* Org switching lives in the left-nav OrganizationSwitcher.
                    Org admin links (Members / Billing / Organization) also
                    live in the left-nav only — the avatar menu stays
                    profile/settings/sign-out. */}
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

            {sidebarCollapsed && (
              <Button
                variant="ghost"
                size="icon"
                aria-label="Expand navigation"
                aria-expanded={!sidebarCollapsed}
                onClick={() => setSidebarCollapsed(false)}
                data-testid="mobile-nav-toggle"
                className="h-9 w-9 shrink-0 text-muted-foreground hover:text-foreground md:hidden"
              >
                <Menu className="h-5 w-5" />
              </Button>
            )}
          </div>
        </header>

        {/* Page Content */}
        <main className="dashboard-main min-h-0 flex-1 overflow-x-hidden overflow-y-auto px-3 py-4 sm:px-5 sm:py-6 lg:px-6 lg:py-8">
          <div className="dashboard-page mx-auto w-full min-w-0 max-w-[1440px]">
            {children}
          </div>
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
      data-tour={`nav-${item.tourId}`}
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
