-- =====================================================
-- RATEL MOVEMENT - YOUTUBE/INSTAGRAM LINKS TABLE
-- Run this SQL in your Supabase SQL Editor
-- =====================================================

-- =====================================================
-- IMPORTANT: STORAGE BUCKET SETUP
-- =====================================================
-- You must also create a storage bucket for thumbnails:
--
-- 1. Go to Supabase Dashboard > Storage
-- 2. Click "New Bucket"
-- 3. Name: "messages"
-- 4. Toggle "Public bucket" to ON (this is REQUIRED for images to display)
-- 5. Click "Create bucket"
--
-- Alternatively, run this SQL to create the bucket:
-- INSERT INTO storage.buckets (id, name, public) VALUES ('messages', 'messages', true)
-- ON CONFLICT (id) DO UPDATE SET public = true;
-- =====================================================

CREATE TABLE IF NOT EXISTS public.youtube_ig_links (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Content
    title VARCHAR(255) NOT NULL,
    subtitle TEXT,
    youtube_url TEXT,  -- YouTube video/channel URL (for YouTube links)
    ig_url TEXT,       -- Instagram post/profile URL (for Instagram links)
    thumbnail_url TEXT, -- Thumbnail image stored in messages bucket

    -- Display settings
    display_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_youtube_ig_active ON public.youtube_ig_links(is_active, display_order);
CREATE INDEX IF NOT EXISTS idx_youtube_ig_youtube ON public.youtube_ig_links(youtube_url) WHERE youtube_url IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_youtube_ig_instagram ON public.youtube_ig_links(ig_url) WHERE ig_url IS NOT NULL;

-- Enable Row Level Security
ALTER TABLE public.youtube_ig_links ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist
DROP POLICY IF EXISTS "Allow public read active youtube_ig_links" ON public.youtube_ig_links;
DROP POLICY IF EXISTS "Allow service role full access youtube_ig_links" ON public.youtube_ig_links;

-- Allow public to read active links
CREATE POLICY "Allow public read active youtube_ig_links" ON public.youtube_ig_links
    FOR SELECT USING (is_active = true);

-- Allow service role full access (for admin dashboard)
CREATE POLICY "Allow service role full access youtube_ig_links" ON public.youtube_ig_links
    FOR ALL USING (auth.role() = 'service_role');

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_youtube_ig_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Drop trigger if exists
DROP TRIGGER IF EXISTS update_youtube_ig_updated_at ON public.youtube_ig_links;

-- Trigger to auto-update timestamp
CREATE TRIGGER update_youtube_ig_updated_at
    BEFORE UPDATE ON public.youtube_ig_links
    FOR EACH ROW
    EXECUTE FUNCTION update_youtube_ig_timestamp();
