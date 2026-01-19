-- ==============================================================================
-- Supabase Realtime Setup for AI Voice Agent Platform
-- ==============================================================================
--
-- Purpose:
--   Enable real-time database subscriptions for automatic UI synchronization
--
-- Use Case:
--   When OAuth tokens are auto-refreshed by backend, or when tools are
--   configured/disabled, the frontend UI should automatically update without
--   requiring a page refresh. This script sets up Supabase Realtime to
--   broadcast database changes to the frontend.
--
-- When to Run:
--   ONE-TIME SETUP: Run this script in Supabase SQL Editor once
--   No changes needed after initial setup
--
-- ==============================================================================

-- Enable realtime on tables that need real-time UI updates
-- This allows Supabase to push database changes to connected frontend clients

ALTER PUBLICATION supabase_realtime ADD TABLE agent_tools;
ALTER PUBLICATION supabase_realtime ADD TABLE voice_agents;

-- Create RLS policy to allow authenticated users to subscribe to realtime changes
-- Note: This only grants SELECT permission for listening to changes
-- Actual data access is controlled by existing RLS policies on each table

CREATE POLICY "Allow authenticated users to subscribe to agent_tools changes"
ON agent_tools
FOR SELECT
TO authenticated
USING (true);

CREATE POLICY "Allow authenticated users to subscribe to voice_agents changes"
ON voice_agents
FOR SELECT
TO authenticated
USING (true);

-- Verification query (run this to confirm setup)
-- Expected output: agent_tools and voice_agents should be listed

SELECT *
FROM pg_publication_tables
WHERE pubname = 'supabase_realtime'
ORDER BY tablename;
