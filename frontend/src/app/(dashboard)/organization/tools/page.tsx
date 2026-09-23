"use client";

import { useSearchParams } from "next/navigation";
import { OrganizationToolsManager } from "@/components/tools/organization-tools-manager";
import { useOrganization } from "@/contexts/organization-context";
import { useUserPermissions } from "@/hooks/use-user-permissions";

/** Organization-level catalog controls for published platform tools. */
export default function OrganizationToolsPage() {
  const searchParams = useSearchParams();
  const { currentOrganization } = useOrganization();
  const { canUpdateOrganization } = useUserPermissions();
  const orgId = searchParams.get("org_id") ?? currentOrganization?.id ?? null;

  if (!orgId) {
    return (
      <div className="flex h-64 flex-col items-center justify-center text-center">
        <p className="text-muted-foreground">
          Select an organization to manage its tools.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-foreground sm:text-2xl">Organization Tools</h1>
        <p className="text-sm text-muted-foreground">
          Control which published tools your organization can connect to new
          voice agents.
        </p>
      </div>
      <OrganizationToolsManager
        orgId={orgId}
        canEdit={canUpdateOrganization}
      />
    </div>
  );
}
