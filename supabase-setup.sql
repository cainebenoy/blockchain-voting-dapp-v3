-- ============================================================
-- VoteChain V3 - Service Discovery Infrastructure
-- ============================================================
-- This creates a configuration table for dynamic backend URL discovery
-- Run this in Supabase SQL Editor before deploying with Cloudflare Tunnel

-- 1. Create the Config Table
CREATE TABLE IF NOT EXISTS public.system_config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

-- 2. Insert the initial placeholder row
INSERT INTO public.system_config (key, value)
VALUES ('backend_url', 'https://waiting-for-tunnel.com')
ON CONFLICT (key) DO NOTHING;

-- 3. Enable Row Level Security (RLS)
ALTER TABLE public.system_config ENABLE ROW LEVEL SECURITY;

-- 4. Drop existing policies if they exist (for re-running script)
DROP POLICY IF EXISTS "Allow public read access" ON public.system_config;
DROP POLICY IF EXISTS "Allow backend update" ON public.system_config;

-- 5. Policy: Allow PUBLIC Read Access (So your frontend works)
CREATE POLICY "Allow public read access" 
ON public.system_config FOR SELECT 
USING (true);

-- 6. Policy: Allow SERVICE ROLE (Backend) Update Access
-- Note: Service role key bypasses RLS, but this policy documents intent
CREATE POLICY "Allow backend update" 
ON public.system_config FOR UPDATE 
USING (true) 
WITH CHECK (true);

-- 7. Create a function to auto-update timestamp
CREATE OR REPLACE FUNCTION update_system_config_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = timezone('utc'::text, now());
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 8. Create trigger for auto-updating timestamp
DROP TRIGGER IF EXISTS update_system_config_timestamp_trigger ON public.system_config;
CREATE TRIGGER update_system_config_timestamp_trigger
    BEFORE UPDATE ON public.system_config
    FOR EACH ROW
    EXECUTE FUNCTION update_system_config_timestamp();

-- Verify setup
SELECT * FROM public.system_config;
