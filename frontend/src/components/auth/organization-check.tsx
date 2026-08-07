"use client";

import React, { useEffect, useState } from "react";
import { useAuth } from "@/contexts/auth-context";
import { useOrganization } from "@/contexts/organization-context";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import type { OrganizationCheckProps } from "@/types/auth";

/**
 * Gates dashboard access on organization membership and founder onboarding.
 *
 * Redirect rules:
 * - No organizations → `/auth/create-organization`
 * - Current org unfinished **and** user is org_admin/platform_admin → `/onboarding`
 * - Invited members (`regular_user`) skip founder onboarding and stay on the dashboard
 *
 * @param children Dashboard content rendered once checks pass
 */
export function OrganizationCheck({ children }: OrganizationCheckProps) {
  const { user, loading: authLoading } = useAuth();
  const {
    organizations,
    currentOrganization,
    loading: orgLoading,
    error: orgError,
    refreshOrganizations,
  } = useOrganization();
  const router = useRouter();
  const [checking, setChecking] = useState(true);
  const [hasRefreshed, setHasRefreshed] = useState(false);
  const [redirecting, setRedirecting] = useState(false);

  useEffect(() => {
    const checkOrganization = async () => {
      if (authLoading || orgLoading || !user || redirecting) {
        return;
      }

      // If there's an error loading organizations, allow access but log the issue
      if (orgError) {
        console.warn(
          "Error loading organizations in OrganizationCheck, allowing access:",
          orgError,
        );
        setChecking(false);
        return;
      }

      if (organizations.length === 0) {
        if (!hasRefreshed) {
          // Try to refresh organizations in case they were just created
          setHasRefreshed(true);
          try {
            await refreshOrganizations();
          } catch (err) {
            console.error("Error refreshing organizations:", err);
          }
          // After refresh, the useEffect will run again with updated organizations
          return;
        } else {
          // Already refreshed and still no organizations, redirect to creation
          setRedirecting(true);
          router.replace("/auth/create-organization");
          return;
        }
      }

      // Founder onboarding only: org admins of an unfinished org.
      // Invited members (typically regular_user) skip the wizard and land on
      // the dashboard even if the inviting org has not finished onboarding.
      const canRunFounderOnboarding =
        !!user &&
        !!currentOrganization &&
        (user.hasRole("org_admin", currentOrganization.id) ||
          user.hasRole("platform_admin"));

      if (
        currentOrganization &&
        currentOrganization.onboarding_completed === false &&
        canRunFounderOnboarding
      ) {
        setRedirecting(true);
        router.replace("/onboarding");
        return;
      }

      setChecking(false);
    };

    checkOrganization();
  }, [
    user,
    authLoading,
    orgLoading,
    organizations,
    currentOrganization,
    orgError,
    router,
    refreshOrganizations,
    hasRefreshed,
    redirecting,
  ]);

  // Show loading state while checking
  if (authLoading || orgLoading || checking) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-12 w-12 animate-spin text-blue-600 mx-auto" />
          <p className="mt-4 text-gray-600">
            Checking your organization status...
          </p>
        </div>
      </div>
    );
  }

  // If user doesn't have an organization, don't render children (they'll be redirected)
  if (!checking && organizations.length === 0) {
    return null;
  }

  // If user has an organization, render children
  return <>{children}</>;
}
