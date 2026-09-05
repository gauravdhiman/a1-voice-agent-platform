"use client";

import { useAgentDetailPage } from "../agent-detail-page-client";
import { AgentDetailSettingsTab } from "../agent-detail-settings-tab";

/** Client entry point for the agent Settings route. */
export default function AgentDetailSettingsPage() {
  const {
    agent,
    agentForm,
    setAgentForm,
    canEdit,
    isPlatformAdmin,
    assignedPhoneNumber,
    setAssignedPhoneNumber,
  } = useAgentDetailPage();

  return (
    <AgentDetailSettingsTab
      agent={agent}
      agentForm={agentForm}
      setAgentForm={setAgentForm}
      canEdit={canEdit}
      isPlatformAdmin={isPlatformAdmin}
      assignedPhoneNumber={assignedPhoneNumber}
      setAssignedPhoneNumber={setAssignedPhoneNumber}
    />
  );
}
