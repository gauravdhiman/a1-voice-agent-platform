"use client";

import { useUserPermissions } from "@/hooks/use-user-permissions";
import { useOrganization } from "@/contexts/organization-context";
import { AccessDenied } from "@/components/ui/access-denied";
import { AgentCreateWidget } from "@/components/agents/agent-create-widget";

/**
 * /agents/create — page-level permission gate (CRIT frontend leak).
 *
 * The "New Agent" button on /agents is gated on `canCreateAgent`
 * (`agent:create` from `/me.permissions`), but the /agents/create URL
 * is reachable by direct navigation. This page-level guard closes the
 * gap using the same permission flag so Phase 2 custom roles with
 * `agent:create` work without a second rewrite.
 */
export default function CreateAgentPage() {
  const { currentOrganization } = useOrganization();
  const { canCreateAgent } = useUserPermissions();

  if (!canCreateAgent) {
    return (
      <AccessDenied
        title="Access Denied"
        description="You need permission to create agents in this organization."
        redirectPath="/agents"
      />
    );
  }

  return (
    <div className="mx-auto w-full max-w-4xl px-0 py-4 sm:py-8">
      <AgentCreateWidget />
    </div>
  );
}
