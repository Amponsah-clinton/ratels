-- =====================================================
-- SITE CONTENT - Supabase Database Schema
-- For managing manifesto, about content, and site settings
-- =====================================================

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =====================================================
-- SITE CONTENT TABLE
-- For manifesto, hero text, and other editable content
-- =====================================================
CREATE TABLE IF NOT EXISTS site_content (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    content_key TEXT UNIQUE NOT NULL,
    title TEXT,
    content TEXT NOT NULL,
    subtitle TEXT,
    image_url TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    display_order INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert default manifesto
INSERT INTO site_content (content_key, title, content, subtitle, is_active) VALUES
(
    'manifesto',
    'Our Manifesto',
    'We stand for truth in an age of deception.
We fight for justice where corruption thrives.
We amplify voices silenced by power.
We document what they want forgotten.
We build bridges where walls divide.
We are the ratel—fearless, relentless, unstoppable.',
    'The Ratel Movement',
    TRUE
) ON CONFLICT (content_key) DO NOTHING;

-- Index for quick lookup
CREATE INDEX IF NOT EXISTS idx_site_content_key ON site_content(content_key);
CREATE INDEX IF NOT EXISTS idx_site_content_active ON site_content(is_active) WHERE is_active = TRUE;

-- =====================================================
-- RLS Policies (Row Level Security)
-- =====================================================

-- Enable RLS
ALTER TABLE site_content ENABLE ROW LEVEL SECURITY;

-- Policy: Anyone can read active content
CREATE POLICY "Allow public read access to active content" ON site_content
    FOR SELECT USING (is_active = TRUE);

-- Policy: Service role can do everything
CREATE POLICY "Allow service role full access" ON site_content
    FOR ALL USING (TRUE) WITH CHECK (TRUE);
