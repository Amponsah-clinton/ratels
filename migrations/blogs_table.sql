-- =====================================================
-- RATEL MOVEMENT - BLOGS TABLE
-- Run this SQL in your Supabase SQL Editor
-- =====================================================

-- =====================================================
-- IMPORTANT: STORAGE BUCKET SETUP
-- =====================================================
-- You must also create a storage bucket for blog images:
--
-- 1. Go to Supabase Dashboard > Storage
-- 2. Click "New Bucket"
-- 3. Name: "blogs"
-- 4. Toggle "Public bucket" to ON (this is REQUIRED for images to display)
-- 5. Click "Create bucket"
--
-- Alternatively, run this SQL to create the bucket:
-- INSERT INTO storage.buckets (id, name, public) VALUES ('blogs', 'blogs', true)
-- ON CONFLICT (id) DO UPDATE SET public = true;
-- =====================================================

CREATE TABLE IF NOT EXISTS public.blogs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Content
    title VARCHAR(255) NOT NULL,
    slug VARCHAR(255) UNIQUE NOT NULL,
    excerpt TEXT,
    content TEXT NOT NULL,  -- Rich text HTML content
    featured_image_url TEXT,

    -- Metadata
    author_name VARCHAR(255) DEFAULT 'Ratel Movement',
    author_email VARCHAR(255),
    published_at TIMESTAMPTZ,
    reading_time INTEGER,  -- Estimated reading time in minutes

    -- SEO & Display
    meta_description TEXT,
    tags TEXT[],  -- Array of tags
    category VARCHAR(100) DEFAULT 'general',
    is_featured BOOLEAN DEFAULT false,
    is_published BOOLEAN DEFAULT false,
    view_count INTEGER DEFAULT 0,

    -- Ordering
    display_order INTEGER DEFAULT 0,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_blogs_slug ON public.blogs(slug);
CREATE INDEX IF NOT EXISTS idx_blogs_published ON public.blogs(is_published, published_at DESC);
CREATE INDEX IF NOT EXISTS idx_blogs_featured ON public.blogs(is_featured);
CREATE INDEX IF NOT EXISTS idx_blogs_category ON public.blogs(category);
CREATE INDEX IF NOT EXISTS idx_blogs_created ON public.blogs(created_at DESC);

-- Enable Row Level Security
ALTER TABLE public.blogs ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist
DROP POLICY IF EXISTS "Allow public read published blogs" ON public.blogs;
DROP POLICY IF EXISTS "Allow service role full access blogs" ON public.blogs;

-- Allow public to read published blogs
CREATE POLICY "Allow public read published blogs" ON public.blogs
    FOR SELECT USING (is_published = true);

-- Allow service role full access (for admin dashboard)
CREATE POLICY "Allow service role full access blogs" ON public.blogs
    FOR ALL USING (auth.role() = 'service_role');

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_blogs_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Drop trigger if exists
DROP TRIGGER IF EXISTS update_blogs_updated_at ON public.blogs;

-- Trigger to auto-update timestamp
CREATE TRIGGER update_blogs_updated_at
    BEFORE UPDATE ON public.blogs
    FOR EACH ROW
    EXECUTE FUNCTION update_blogs_timestamp();

-- Function to generate slug from title
CREATE OR REPLACE FUNCTION generate_blog_slug(title_text VARCHAR)
RETURNS VARCHAR AS $$
DECLARE
    slug_text VARCHAR;
    counter INTEGER := 0;
BEGIN
    -- Convert to lowercase, replace spaces with hyphens, remove special chars
    slug_text := lower(regexp_replace(title_text, '[^a-z0-9]+', '-', 'g'));
    slug_text := trim(both '-' from slug_text);
    
    -- Ensure uniqueness
    WHILE EXISTS (SELECT 1 FROM public.blogs WHERE slug = slug_text) LOOP
        counter := counter + 1;
        slug_text := slug_text || '-' || counter;
    END LOOP;
    
    RETURN slug_text;
END;
$$ LANGUAGE plpgsql;
