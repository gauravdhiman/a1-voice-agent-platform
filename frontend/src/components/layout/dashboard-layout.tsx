'use client';

import React, { useState } from 'react';
import { useRouter, usePathname, useSearchParams } from 'next/navigation';
import { useAuth } from '@/contexts/auth-context';
import { useOrganization } from '@/contexts/organization-context';
import {
  LayoutDashboard,
  Building2,
  Users,
  CreditCard,
  Settings,
  ChevronLeft,
  ChevronRight,
  LogOut,
  Bot,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuItemLink,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
  DropdownMenuLabel,
} from '@/components/ui/dropdown-menu';
import { ThemeToggle } from '@/components/ui/theme-toggle';
import { NavigationLink } from '@/components/ui/navigation-link';

interface DashboardLayoutProps {
  children: React.ReactNode;
}

const navigationItems = [
  {
    name: 'Dashboard',
    href: '/dashboard',
    icon: LayoutDashboard,
  },
  {
    name: 'Agents',
    href: '/agents',
    icon: Bot,
  },
  {
    name: 'Users',
    href: '/users',
    icon: Users,
  },
];

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
      console.error('Error signing out:', error);
    } else {
      router.push('/auth/signin');
    }
  };

  // Check if user is a platform admin
  const isPlatformAdmin = user?.hasRole('platform_admin');

  // Filter navigation items based on user permissions
  const filteredNavigationItems = navigationItems.filter(item => {
    if (item.name === 'Users') {
      return isPlatformAdmin; // Only show Users to platform admins
    }
    return true; // Show all other items
  });

  const getInitials = (name: string) => {
    return name
      .split(' ')
      .map(n => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);
  };

  const getBreadcrumbs = () => {
    const breadcrumbs = [];
    const orgId = searchParams.get('org_id');

    if (pathname === '/dashboard') {
      breadcrumbs.push({ name: 'Dashboard', href: null });
    } else if (pathname === '/organizations') {
      breadcrumbs.push({ name: 'Organizations', href: null });
    } else if (pathname === '/organization') {
      breadcrumbs.push({ name: 'Organization', href: null });
    } else if (pathname === '/organization/members') {
      const orgHref = orgId ? `/organization?org_id=${orgId}` : '/organization';
      breadcrumbs.push({ name: 'Organization', href: orgHref });
      breadcrumbs.push({ name: 'Members', href: null });

    } else if (pathname === '/agents') {
      breadcrumbs.push({ name: 'Agents', href: null });
    } else if (pathname.startsWith('/agents/') && pathname.split('/').length === 3) {
      breadcrumbs.push({ name: 'Agents', href: '/agents' });
      breadcrumbs.push({ name: 'Agent Details', href: null });
    } else if (pathname === '/users') {
      if (isPlatformAdmin) {
        breadcrumbs.push({ name: 'Users', href: null });
      } else {
        breadcrumbs.push({ name: 'Dashboard', href: null });
      }
    } else if (pathname === '/organization/billing') {
      const orgHref = orgId ? `/organization?org_id=${orgId}` : '/organization';
      breadcrumbs.push({ name: 'Organization', href: orgHref });
      breadcrumbs.push({ name: 'Billing', href: null });
    } else if (pathname === '/settings') {
      breadcrumbs.push({ name: 'Settings', href: null });
    } else if (pathname.startsWith('/organization')) {
      const orgHref = orgId ? `/organization?org_id=${orgId}` : '/organization';
      if (pathname.includes('/members')) {
        breadcrumbs.push({ name: 'Organization', href: orgHref });
        breadcrumbs.push({ name: 'Members', href: null });

      } else {
        breadcrumbs.push({ name: 'Organization', href: null });
      }
    } else {
      breadcrumbs.push({ name: 'Dashboard', href: null });
    }

    return breadcrumbs;
  };

  return (
    <div className="h-screen bg-background flex overflow-hidden font-sans">
      {/* Sidebar */}
      <aside
        className={`bg-sidebar border-r border-sidebar-border shadow-sm transition-all duration-300 ease-in-out ${sidebarCollapsed ? 'w-16' : 'w-64'
          } flex flex-col h-full z-20`}
      >
        {/* Sidebar Header */}
        <div className="h-14 flex items-center justify-between px-4 border-b border-sidebar-border bg-sidebar">
          {!sidebarCollapsed && (
            <div className="flex items-center space-x-2">
              <div className="bg-sidebar-primary w-7 h-7 rounded-md flex items-center justify-center">
                <span className="text-sidebar-primary-foreground font-bold text-base">AI</span>
              </div>
              <span className="text-base font-bold text-sidebar-foreground tracking-tight">NeuraSaaS</span>
            </div>
          )}
          {sidebarCollapsed && (
            <div className="mx-auto bg-sidebar-primary w-7 h-7 rounded-md flex items-center justify-center">
              <span className="text-sidebar-primary-foreground font-bold text-base">AI</span>
            </div>
          )}
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
            className={`h-8 w-8 text-sidebar-foreground/50 hover:text-sidebar-foreground hover:bg-sidebar-accent ${sidebarCollapsed ? 'hidden' : ''}`}
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
        </div>

        {/* Navigation */}
        <div className="flex-1 py-4 px-3 space-y-1 overflow-y-auto">
          {filteredNavigationItems.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href ||
              (item.href === '/organizations' && pathname.startsWith('/organizations'));

            return (
              <NavigationLink
                key={item.name}
                href={item.href}
                title={sidebarCollapsed ? item.name : undefined}
                exact={item.href !== '/organizations'}
                className={sidebarCollapsed ? 'justify-center' : ''}
              >
                <Icon className={`h-4 w-4 flex-shrink-0 ${isActive ? 'text-sidebar-primary' : 'text-sidebar-foreground/50 group-hover:text-sidebar-foreground'}`} />
                {!sidebarCollapsed && <span>{item.name}</span>}
                {sidebarCollapsed && isActive && (
                  <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-6 bg-sidebar-primary rounded-r-full" />
                )}
              </NavigationLink>
            );
          })}
        </div>

        {/* Sidebar Footer */}
        <div className="p-3 border-t border-sidebar-border bg-sidebar">
          <div className={`flex items-center ${sidebarCollapsed ? 'justify-center' : 'space-x-3'}`}>
            <Avatar className="h-8 w-8 border border-sidebar-border">
              <AvatarFallback className="bg-sidebar-primary/10 text-sidebar-primary font-medium text-xs">
                {user?.firstName ? getInitials(`${user.firstName} ${user.lastName || ''}`) : 'U'}
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
            {/* Search and Notifications - Hidden for now as they are not yet functional */}
            {/* <div className="relative hidden md:block w-64">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                type="search"
                placeholder="Search..."
                className="pl-9 h-9 bg-muted/50 border-none focus-visible:ring-1 focus-visible:ring-primary"
              />
            </div>

            <Button variant="ghost" size="icon" className="text-muted-foreground hover:text-foreground relative">
              <Bell className="h-5 w-5" />
              <span className="absolute top-2 right-2 h-2 w-2 bg-red-500 rounded-full border-2 border-background"></span>
            </Button> */}

            <ThemeToggle />

            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" className="relative h-8 w-8 rounded-full p-0 ring-2 ring-transparent hover:ring-primary/20 transition-all">
                  <Avatar className="h-8 w-8">
                    <AvatarFallback className="bg-primary text-primary-foreground font-medium text-xs">
                      {user?.firstName ? getInitials(`${user.firstName} ${user.lastName || ''}`) : 'U'}
                    </AvatarFallback>
                  </Avatar>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56 p-2">
                <DropdownMenuLabel className="font-normal">
                  <div className="flex flex-col space-y-1">
                    <p className="text-sm font-medium leading-none">{user?.firstName} {user?.lastName}</p>
                    <p className="text-xs leading-none text-muted-foreground">{user?.email}</p>
                  </div>
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItemLink href="/settings">
                  <Settings className="mr-2 h-4 w-4" />
                  <span>Settings</span>
                </DropdownMenuItemLink>
                {currentOrganization && user && (user.hasRole('platform_admin') || user.hasRole('org_admin', currentOrganization.id)) && (
                  <>
                    <DropdownMenuSeparator />
                    <DropdownMenuLabel>Organization</DropdownMenuLabel>
                    {organizations.length > 1 && (
                      <DropdownMenuItemLink href="/organizations">
                        <Building2 className="mr-2 h-4 w-4" />
                        <span>Switch Org</span>
                      </DropdownMenuItemLink>
                    )}
                    {organizations.length === 1 && currentOrganization && (
                      <>
                        <DropdownMenuItemLink href={`/organization?org_id=${currentOrganization.id}`}>
                          <Building2 className="mr-2 h-4 w-4" />
                          <span>Overview</span>
                        </DropdownMenuItemLink>

                        <DropdownMenuItemLink href={`/organization/members?org_id=${currentOrganization.id}`}>
                          <Users className="mr-2 h-4 w-4" />
                          <span>Members</span>
                        </DropdownMenuItemLink>
                        <DropdownMenuItemLink href={`/organization/billing?org_id=${currentOrganization.id}`}>
                          <CreditCard className="mr-2 h-4 w-4" />
                          <span>Billing</span>
                        </DropdownMenuItemLink>
                      </>
                    )}
                    <DropdownMenuSeparator />
                  </>
                )}
                <DropdownMenuItem onClick={handleSignOut} className="text-destructive focus:text-destructive cursor-pointer">
                  <LogOut className="mr-2 h-4 w-4" />
                  <span>Sign out</span>
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 overflow-y-auto p-4">
          <div className="max-w-6xl mx-auto">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
