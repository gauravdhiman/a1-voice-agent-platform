"use client";

import { useEffect } from "react";
import { toast } from "sonner";
import { consumeInviteWelcome } from "@/lib/invite-welcome";
import { useOrganization } from "@/contexts/organization-context";

/**
 * Shows a one-shot welcome toast after an invited user lands on the dashboard.
 *
 * Invite signup/OAuth flows set a sessionStorage flag; this component consumes
 * it once and greets the user with the organization name when available.
 */
export function InviteWelcomeToast() {
  const { currentOrganization, loading } = useOrganization();

  useEffect(() => {
    if (loading) {
      return;
    }

    const pending = consumeInviteWelcome();
    if (!pending) {
      return;
    }

    const organizationName =
      pending.organizationName || currentOrganization?.name || null;

    toast.success(
      organizationName
        ? `Welcome to ${organizationName}! You're all set.`
        : "Welcome! You've joined the organization.",
    );
  }, [loading, currentOrganization?.name]);

  return null;
}
