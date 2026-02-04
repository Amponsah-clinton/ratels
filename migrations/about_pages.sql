-- =====================================================
-- RATEL MOVEMENT - ABOUT PAGES TABLE
-- Run this SQL in your Supabase SQL Editor
-- Stores content for About Ratel and Mission & Vision pages
-- =====================================================

CREATE TABLE IF NOT EXISTS public.about_pages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Page: 'about_ratel' | 'mission_vision'
    page_key VARCHAR(50) NOT NULL,

    -- Section identifier (e.g. 'hero', 'mission', 'vision', 'values', 'value_1')
    section_key VARCHAR(100) NOT NULL,

    -- Content
    title TEXT,
    subtitle TEXT,
    content TEXT,
    icon VARCHAR(50),
    highlight_text TEXT,
    section_order INTEGER DEFAULT 0,
    image_url TEXT,

    -- Display
    is_active BOOLEAN DEFAULT true,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(page_key, section_key)
);

CREATE INDEX IF NOT EXISTS idx_about_pages_page_key ON public.about_pages(page_key);
CREATE INDEX IF NOT EXISTS idx_about_pages_section_order ON public.about_pages(page_key, section_order);
CREATE INDEX IF NOT EXISTS idx_about_pages_active ON public.about_pages(is_active);

ALTER TABLE public.about_pages ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Allow public read about_pages" ON public.about_pages;
DROP POLICY IF EXISTS "Allow service role full access about_pages" ON public.about_pages;

CREATE POLICY "Allow public read about_pages" ON public.about_pages
    FOR SELECT USING (is_active = true);

CREATE POLICY "Allow service role full access about_pages" ON public.about_pages
    FOR ALL USING (auth.role() = 'service_role');

CREATE OR REPLACE FUNCTION update_about_pages_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_about_pages_updated_at ON public.about_pages;
CREATE TRIGGER update_about_pages_updated_at
    BEFORE UPDATE ON public.about_pages
    FOR EACH ROW
    EXECUTE FUNCTION update_about_pages_timestamp();
