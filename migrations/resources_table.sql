-- =====================================================
-- RATEL MOVEMENT - RESOURCES TABLE
-- Run this SQL in your Supabase SQL Editor
-- Fixes: 404 Not Found for /rest/v1/resources
-- =====================================================

CREATE TABLE IF NOT EXISTS public.resources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Content
    title TEXT NOT NULL,
    description TEXT,
    category TEXT NOT NULL,

    -- File
    file_url TEXT,
    file_name TEXT,
    file_type TEXT,

    -- Metadata
    intended_audience TEXT,
    how_to_use TEXT,
    author TEXT,
    version TEXT,
    tags TEXT[],

    -- Display
    is_featured BOOLEAN DEFAULT false,
    status TEXT NOT NULL DEFAULT 'active',
    display_order INTEGER DEFAULT 0,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_resources_status ON public.resources(status);
CREATE INDEX IF NOT EXISTS idx_resources_category ON public.resources(category);
CREATE INDEX IF NOT EXISTS idx_resources_display_order ON public.resources(display_order);
CREATE INDEX IF NOT EXISTS idx_resources_created ON public.resources(created_at DESC);

-- Enable Row Level Security
ALTER TABLE public.resources ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist
DROP POLICY IF EXISTS "Allow public read active resources" ON public.resources;
DROP POLICY IF EXISTS "Allow service role full access resources" ON public.resources;

-- Allow public to read active resources (for public/member pages)
CREATE POLICY "Allow public read active resources" ON public.resources
    FOR SELECT USING (status = 'active');

-- Allow service role full access (for admin dashboard)
CREATE POLICY "Allow service role full access resources" ON public.resources
    FOR ALL USING (auth.role() = 'service_role');

-- Trigger to auto-update updated_at
CREATE OR REPLACE FUNCTION update_resources_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_resources_updated_at ON public.resources;

CREATE TRIGGER update_resources_updated_at
    BEFORE UPDATE ON public.resources
    FOR EACH ROW
    EXECUTE FUNCTION update_resources_timestamp();
