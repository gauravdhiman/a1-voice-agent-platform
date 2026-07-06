"use client";

import { useUserPermissions } from "@/hooks/use-user-permissions";
import { useOrganization } from "@/contexts/organization-context";
import { AccessDenied } from "@/components/ui/access-denied";
import { AgentCreateWidget } from "@/components/agents/agent-create-widget";

/**
 * /agents/create — page-level admin gate (CRIT frontend leak).
 *
 * The "New Agent" button on /agents is gated on org_admin or
 * platform_admin, but the /agents/create URL is reachable by direct
 * navigation. This page-level guard closes the gap.
 */
export default function CreateAgentPage() {
  const { currentOrganization } = useOrganization();
  const { isPlatformAdmin, isOrgAdmin } = useUserPermissions();

  if (!isPlatformAdmin && !isOrgAdmin) {
    return (
      <AccessDenied
        title="Access Denied"
        description="Only organization admins and platform admins can create agents."
        redirectPath="/agents"
      />
    );
  }

  return (
    <div className="container mx-auto py-8">
      <AgentCreateWidget />
    </div>
  );
}
