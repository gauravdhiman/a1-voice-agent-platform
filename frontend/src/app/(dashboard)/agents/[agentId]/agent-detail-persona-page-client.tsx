"use client";

import { useAgentDetailPage } from "./agent-detail-page-client";
import { AgentDetailPersonaTab } from "./agent-detail-persona-tab";

/** Client entry point for the lightweight default Persona route. */
export default function AgentDetailPersonaPageClient() {
  const { agent, agentForm, setAgentForm, canEdit } = useAgentDetailPage();

  return (
    <AgentDetailPersonaTab
      agentId={agent.id}
      agentForm={agentForm}
      setAgentForm={setAgentForm}
      canEdit={canEdit}
    />
  );
}
