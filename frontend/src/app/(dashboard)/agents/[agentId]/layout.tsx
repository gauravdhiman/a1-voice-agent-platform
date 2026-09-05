import AgentDetailPageClient from "./agent-detail-page-client";

/**
 * Keeps the agent editor and its unsaved form state mounted while navigating
 * between the nested Persona, Skills, Tools, Settings, and Call History routes.
 */
export default function AgentDetailLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return <AgentDetailPageClient>{children}</AgentDetailPageClient>;
}
