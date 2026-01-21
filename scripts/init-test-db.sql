-- Initialize test database with Supabase-specific schemas and functions
CREATE SCHEMA IF NOT EXISTS auth;

-- Create Supabase standard roles if they don't exist
DO $$ 
BEGIN
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'authenticated') THEN
    CREATE ROLE authenticated;
  END IF;
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'anon') THEN
    CREATE ROLE anon;
  END IF;
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'service_role') THEN
    CREATE ROLE service_role;
  END IF;
END
$$;

-- Create a dummy users table that migrations expect
CREATE TABLE IF NOT EXISTS auth.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Mock the auth.uid() function used in RLS policies
CREATE OR REPLACE FUNCTION auth.uid() 
RETURNS UUID AS $$ 
    SELECT '00000000-0000-0000-0000-000000000000'::UUID; 
$$ LANGUAGE SQL;

-- Ensure gen_random_uuid() is available
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
