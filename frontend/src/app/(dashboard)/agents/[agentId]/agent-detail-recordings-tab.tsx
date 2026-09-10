"use client";

import { AgentCallRecordings } from "@/components/calls/agent-call-recordings";
import type { VoiceAgent } from "@/types/agent";

interface AgentDetailRecordingsTabProps {
  agent: VoiceAgent;
}

/** Call history is isolated from the initial agent-detail bundle. */
export function AgentDetailRecordingsTab({
  agent,
}: AgentDetailRecordingsTabProps) {
  return (
    <AgentCallRecordings
      organizationId={agent.organization_id}
      agentId={agent.id}
      agentName={agent.name}
    />
  );
}
