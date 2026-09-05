import { redirect } from "next/navigation";

import {
  getAgentDetailHref,
  normalizeAgentDetailTab,
} from "@/components/agents/agent-detail-tabs";

import AgentDetailPersonaPageClient from "./agent-detail-persona-page-client";

interface AgentDetailPageProps {
  params: Promise<{ agentId: string }>;
  searchParams: Promise<{ tab?: string | string[] }>;
}

/**
 * Keeps legacy query-string links working while routing each feature-heavy
 * agent tab through its own Next.js entry point.
 */
export default async function AgentDetailPage({
  params,
  searchParams,
}: AgentDetailPageProps) {
  const [{ agentId }, query] = await Promise.all([params, searchParams]);
  const rawTab = Array.isArray(query.tab) ? query.tab[0] : query.tab;
  const tab = normalizeAgentDetailTab(rawTab ?? null);

  if (tab !== "persona") {
    redirect(getAgentDetailHref(agentId, tab));
  }

  return <AgentDetailPersonaPageClient />;
}
