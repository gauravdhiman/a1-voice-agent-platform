/**
 * NavigationLink Component
 *
 * A reusable navigation link component that wraps Next.js Link with proper cursor styling
 * and supports active state for navigation items.
 *
 * This component solves two UX issues:
 * 1. Shows pointer cursor on hover (unlike buttons)
 * 2. Supports browser context menu (right-click to open in new tab)
 *
 * USAGE:
 * -------
 * import { NavigationLink } from '@/components/ui/navigation-link';
 *
 * <NavigationLink href="/agents" exact>
 *   <Bot className="h-4 w-4" />
 *   <span>Agents</span>
 * </NavigationLink>
 *
 * With custom styling:
 * <NavigationLink
 *   href="/dashboard"
 *   className="custom-class"
 *   activeClassName="active-class"
 *   baseClassName="base-classes"
 *   inactiveClassName="inactive-classes"
 * >
 *   Dashboard
 * </NavigationLink>
 */

'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';

interface NavigationLinkProps extends React.ComponentProps<typeof Link> {
  children: React.ReactNode;
  activeClassName?: string;
  exact?: boolean;
  baseClassName?: string;
  inactiveClassName?: string;
}

export function NavigationLink({
  children,
  className,
  activeClassName = 'bg-sidebar-accent text-sidebar-accent-foreground font-medium shadow-sm',
  exact = false,
  baseClassName = 'flex items-center space-x-3 px-3 py-2 rounded-md transition-all duration-200 group relative text-sm w-full',
  inactiveClassName = 'text-sidebar-foreground/70 hover:bg-sidebar-accent/50 hover:text-sidebar-foreground',
  href,
  ...props
}: NavigationLinkProps) {
  const pathname = usePathname();
  const isActive = exact 
    ? pathname === href 
    : pathname === href || pathname.startsWith(String(href));

  return (
    <Link
      href={href}
      className={cn(
        'cursor-pointer',
        baseClassName,
        isActive ? activeClassName : inactiveClassName,
        className
      )}
      {...props}
    >
      {children}
    </Link>
  );
}
