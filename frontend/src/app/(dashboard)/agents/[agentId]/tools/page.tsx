"use client";

import { useAgentDetailPage } from "../agent-detail-page-client";
import { AgentDetailToolsTab } from "../agent-detail-tools-tab";

/** Client entry point for the agent Tools route. */
export default function AgentDetailToolsPage() {
  const { agent, organization, canEdit } = useAgentDetailPage();

  return (
    <AgentDetailToolsTab
      agent={agent}
      organization={organization}
      canEdit={canEdit}
    />
  );
}
