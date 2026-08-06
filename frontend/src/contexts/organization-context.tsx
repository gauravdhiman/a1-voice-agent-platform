"use client";

import React, {
  createContext,
  useContext,
  useEffect,
  useState,
  ReactNode,
} from "react";
import { Organization } from "@/types/organization";
import { useAuth } from "@/contexts/auth-context";
import { useUserOrganizations } from "@/hooks/use-user-organizations";
import { selectPreferredOrganization } from "@/lib/organization-utils";
import { peekInviteWelcome } from "@/lib/invite-welcome";

interface OrganizationContextType {
  organizations: Organization[];
  currentOrganization: Organization | null;
  loading: boolean;
  error: string | null;
  setCurrentOrganization: (org: Organization) => void;
  refreshOrganizations: () => Promise<void>;
}

interface OrganizationProviderProps {
  children: ReactNode;
}

const OrganizationContext = createContext<OrganizationContextType | undefined>(
  undefined,
);

export function OrganizationProvider({ children }: OrganizationProviderProps) {
  const { isAuthenticated, loading: authLoading } = useAuth();
  const [currentOrganization, setCurrentOrganizationState] =
    useState<Organization | null>(null);

  // Use React Query for organizations data
  const {
    data: organizations = [],
    isLoading: loading,
    error: queryError,
    refetch,
  } = useUserOrganizations();

  // Convert React Query error to string for consistency with existing interface
  const error = queryError
    ? queryError instanceof Error
      ? queryError.message
      : "Failed to load organizations"
    : null;

  // Clear current organization when not authenticated
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      setCurrentOrganizationState(null);
    }
  }, [isAuthenticated, authLoading]);

  const setCurrentOrganization = (org: Organization) => {
    setCurrentOrganizationState(org);
    // Optionally persist to localStorage for session persistence
    localStorage.setItem("currentOrganizationId", org.id);
  };

  const refreshOrganizations = async () => {
    await refetch();
  };

  // Initial auto-select: prefer the org just joined via invitation, else the
  // saved selection, else the first membership.
  useEffect(() => {
    if (organizations.length === 0 || currentOrganization) {
      return;
    }

    const savedOrgId =
      typeof window !== "undefined"
        ? localStorage.getItem("currentOrganizationId")
        : null;
    const invitePending = peekInviteWelcome();
    const preferred = selectPreferredOrganization(organizations, savedOrgId, {
      preferredOrganizationId: invitePending?.organizationId,
    });
    if (!preferred) {
      return;
    }

    setCurrentOrganizationState(preferred);
    localStorage.setItem("currentOrganizationId", preferred.id);
  }, [organizations, currentOrganization]);

  // Keep the selected org object in sync when the query refreshes the same id.
  useEffect(() => {
    if (!currentOrganization || organizations.length === 0) {
      return;
    }

    const refreshed = organizations.find(
      (org) => org.id === currentOrganization.id,
    );
    if (
      refreshed &&
      (refreshed.onboarding_completed !==
        currentOrganization.onboarding_completed ||
        refreshed.name !== currentOrganization.name)
    ) {
      setCurrentOrganizationState(refreshed);
    }
  }, [organizations, currentOrganization]);

  const value: OrganizationContextType = {
    organizations,
    currentOrganization,
    loading,
    error,
    setCurrentOrganization,
    refreshOrganizations,
  };

  return (
    <OrganizationContext.Provider value={value}>
      {children}
    </OrganizationContext.Provider>
  );
}

export function useOrganization() {
  const context = useContext(OrganizationContext);
  if (context === undefined) {
    throw new Error(
      "useOrganization must be used within an OrganizationProvider",
    );
  }
  return context;
}
