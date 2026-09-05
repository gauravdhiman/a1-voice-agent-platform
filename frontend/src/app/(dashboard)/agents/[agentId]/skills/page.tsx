"use client";

import { useAgentDetailPage } from "../agent-detail-page-client";
import { AgentDetailSkillsTab } from "../agent-detail-skills-tab";

/** Client entry point for the agent Skills route. */
export default function AgentDetailSkillsPage() {
  const { agent, canEdit } = useAgentDetailPage();

  return <AgentDetailSkillsTab agent={agent} canEdit={canEdit} />;
}
