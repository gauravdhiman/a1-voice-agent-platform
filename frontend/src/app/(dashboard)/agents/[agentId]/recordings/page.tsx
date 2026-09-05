"use client";

import { useAgentDetailPage } from "../agent-detail-page-client";
import { AgentDetailRecordingsTab } from "../agent-detail-recordings-tab";

/** Client entry point for the agent Call History route. */
export default function AgentDetailRecordingsPage() {
  const { agent } = useAgentDetailPage();

  return <AgentDetailRecordingsTab agent={agent} />;
}
