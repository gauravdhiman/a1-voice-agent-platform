"use client";

import React from "react";
import { useCallLogs } from "@/hooks/use-call-logs";
import { CallLogList } from "@/components/calls/call-log-list";

interface AgentCallRecordingsProps {
  /** Organization that owns the agent and its call records. */
  organizationId: string;
  /** Agent whose calls should be displayed. */
  agentId: string;
  /** Agent name used in the panel description and empty state. */
  agentName: string;
}

/**
 * Displays the shared call history view scoped to one agent.
 *
 * The tab intentionally loads all calls for the agent. Recording playback is
 * shown only on rows with a completed recording, matching the organization
 * Calls page while omitting the redundant Agent column.
 */
export function AgentCallRecordings({
  organizationId,
  agentId,
  agentName,
}: AgentCallRecordingsProps) {
  const [page, setPage] = React.useState(1);
  const { data, isLoading, isFetching, error, refetch } = useCallLogs(
    organizationId,
    {
      agent_id: agentId,
      page,
      page_size: 25,
    },
  );

  return (
    <CallLogList
      data={data}
      isLoading={isLoading}
      isFetching={isFetching}
      error={error}
      onRefresh={() => refetch()}
      onPageChange={setPage}
      showAgentColumn={false}
      canViewRecordings
      title="Call History"
      subtitle={`Calls handled by ${agentName}`}
      emptyTitle="No calls yet"
      emptyDescription={`${agentName}'s calls will appear here once the agent starts receiving them.`}
      dataTour="agent-detail-recordings"
    />
  );
}
