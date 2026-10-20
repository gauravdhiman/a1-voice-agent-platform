-- Realtime is owned by Alembic revision 20261019000001 and successors.
-- Never grant client SELECT on voice_agents/agent_tools for subscriptions:
-- SELECT policies also apply to the Data API and expose private tenant data.
-- Apply the reviewed migration, then verify the content-free feed read-only.
SELECT pubname, schemaname, tablename
FROM pg_publication_tables
WHERE pubname = 'supabase_realtime'
ORDER BY schemaname, tablename;
