-- =====================================================
-- MEDIA VAULT - Supabase Database Schema
-- Evidence-focused media management system
-- =====================================================

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =====================================================
-- VIDEOS TABLE
-- Categories: short_clips, documentaries, public_addresses
-- =====================================================
CREATE TABLE IF NOT EXISTS media_videos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title TEXT NOT NULL,
    description TEXT,
    category TEXT NOT NULL CHECK (category IN ('short_clips', 'documentaries', 'public_addresses')),
    file_url TEXT,
    video_link TEXT,
    thumbnail_url TEXT,
    duration_seconds INTEGER,
    file_size_bytes BIGINT,
    mime_type TEXT DEFAULT 'video/mp4',
    tags TEXT[] DEFAULT '{}',
    source TEXT,
    recorded_date DATE,
    location TEXT,
    is_featured BOOLEAN DEFAULT FALSE,
    view_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'archived', 'pending')),
    uploaded_by TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT video_source_check CHECK (file_url IS NOT NULL OR video_link IS NOT NULL)
);

-- Indexes for videos
CREATE INDEX IF NOT EXISTS idx_media_videos_category ON media_videos(category);
CREATE INDEX IF NOT EXISTS idx_media_videos_status ON media_videos(status);
CREATE INDEX IF NOT EXISTS idx_media_videos_created ON media_videos(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_media_videos_featured ON media_videos(is_featured) WHERE is_featured = TRUE;

-- =====================================================
-- AUDIO TABLE
-- Categories: interviews, statements
-- =====================================================
CREATE TABLE IF NOT EXISTS media_audio (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title TEXT NOT NULL,
    description TEXT,
    category TEXT NOT NULL CHECK (category IN ('interviews', 'statements')),
    file_url TEXT NOT NULL,
    cover_image_url TEXT,
    duration_seconds INTEGER,
    file_size_bytes BIGINT,
    mime_type TEXT DEFAULT 'audio/mpeg',
    tags TEXT[] DEFAULT '{}',
    speaker TEXT,
    source TEXT,
    recorded_date DATE,
    transcript TEXT,
    is_featured BOOLEAN DEFAULT FALSE,
    play_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'archived', 'pending')),
    uploaded_by TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for audio
CREATE INDEX IF NOT EXISTS idx_media_audio_category ON media_audio(category);
CREATE INDEX IF NOT EXISTS idx_media_audio_status ON media_audio(status);
CREATE INDEX IF NOT EXISTS idx_media_audio_created ON media_audio(created_at DESC);

-- =====================================================
-- IMAGES TABLE
-- Categories: evidence, campaign_visuals
-- =====================================================
CREATE TABLE IF NOT EXISTS media_images (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title TEXT NOT NULL,
    description TEXT,
    category TEXT NOT NULL CHECK (category IN ('evidence', 'campaign_visuals')),
    file_url TEXT NOT NULL,
    thumbnail_url TEXT,
    width INTEGER,
    height INTEGER,
    file_size_bytes BIGINT,
    mime_type TEXT DEFAULT 'image/jpeg',
    tags TEXT[] DEFAULT '{}',
    alt_text TEXT,
    source TEXT,
    captured_date DATE,
    location TEXT,
    photographer TEXT,
    is_featured BOOLEAN DEFAULT FALSE,
    view_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'archived', 'pending')),
    uploaded_by TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for images
CREATE INDEX IF NOT EXISTS idx_media_images_category ON media_images(category);
CREATE INDEX IF NOT EXISTS idx_media_images_status ON media_images(status);
CREATE INDEX IF NOT EXISTS idx_media_images_created ON media_images(created_at DESC);

-- =====================================================
-- DOCUMENTS TABLE
-- Categories: reports, pdfs, official_letters
-- =====================================================
CREATE TABLE IF NOT EXISTS media_documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title TEXT NOT NULL,
    description TEXT,
    category TEXT NOT NULL CHECK (category IN ('reports', 'pdfs', 'official_letters')),
    file_url TEXT NOT NULL,
    preview_image_url TEXT,
    file_size_bytes BIGINT,
    mime_type TEXT DEFAULT 'application/pdf',
    page_count INTEGER,
    tags TEXT[] DEFAULT '{}',
    author TEXT,
    source TEXT,
    document_date DATE,
    reference_number TEXT,
    is_confidential BOOLEAN DEFAULT FALSE,
    is_featured BOOLEAN DEFAULT FALSE,
    download_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'archived', 'pending')),
    uploaded_by TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for documents
CREATE INDEX IF NOT EXISTS idx_media_documents_category ON media_documents(category);
CREATE INDEX IF NOT EXISTS idx_media_documents_status ON media_documents(status);
CREATE INDEX IF NOT EXISTS idx_media_documents_created ON media_documents(created_at DESC);

-- =====================================================
-- MEDIA VAULT STATISTICS VIEW
-- Aggregated stats for dashboard
-- =====================================================
CREATE OR REPLACE VIEW media_vault_stats AS
SELECT
    'videos' as media_type,
    COUNT(*) as total_count,
    COUNT(*) FILTER (WHERE status = 'active') as active_count,
    COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '30 days') as recent_count,
    COALESCE(SUM(file_size_bytes), 0) as total_size_bytes
FROM media_videos
UNION ALL
SELECT
    'audio' as media_type,
    COUNT(*) as total_count,
    COUNT(*) FILTER (WHERE status = 'active') as active_count,
    COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '30 days') as recent_count,
    COALESCE(SUM(file_size_bytes), 0) as total_size_bytes
FROM media_audio
UNION ALL
SELECT
    'images' as media_type,
    COUNT(*) as total_count,
    COUNT(*) FILTER (WHERE status = 'active') as active_count,
    COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '30 days') as recent_count,
    COALESCE(SUM(file_size_bytes), 0) as total_size_bytes
FROM media_images
UNION ALL
SELECT
    'documents' as media_type,
    COUNT(*) as total_count,
    COUNT(*) FILTER (WHERE status = 'active') as active_count,
    COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '30 days') as recent_count,
    COALESCE(SUM(file_size_bytes), 0) as total_size_bytes
FROM media_documents;

-- =====================================================
-- UPDATED_AT TRIGGER FUNCTION
-- Automatically update updated_at timestamp
-- =====================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply triggers to all tables
DROP TRIGGER IF EXISTS update_media_videos_updated_at ON media_videos;
CREATE TRIGGER update_media_videos_updated_at
    BEFORE UPDATE ON media_videos
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_media_audio_updated_at ON media_audio;
CREATE TRIGGER update_media_audio_updated_at
    BEFORE UPDATE ON media_audio
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_media_images_updated_at ON media_images;
CREATE TRIGGER update_media_images_updated_at
    BEFORE UPDATE ON media_images
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_media_documents_updated_at ON media_documents;
CREATE TRIGGER update_media_documents_updated_at
    BEFORE UPDATE ON media_documents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- ROW LEVEL SECURITY (RLS)
-- =====================================================
ALTER TABLE media_videos ENABLE ROW LEVEL SECURITY;
ALTER TABLE media_audio ENABLE ROW LEVEL SECURITY;
ALTER TABLE media_images ENABLE ROW LEVEL SECURITY;
ALTER TABLE media_documents ENABLE ROW LEVEL SECURITY;

-- Service role has full access
CREATE POLICY "Service role full access videos" ON media_videos
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access audio" ON media_audio
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access images" ON media_images
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access documents" ON media_documents
    FOR ALL USING (auth.role() = 'service_role');

-- Public can view active media
CREATE POLICY "Public can view active videos" ON media_videos
    FOR SELECT USING (status = 'active');

CREATE POLICY "Public can view active audio" ON media_audio
    FOR SELECT USING (status = 'active');

CREATE POLICY "Public can view active images" ON media_images
    FOR SELECT USING (status = 'active');

CREATE POLICY "Public can view active non-confidential documents" ON media_documents
    FOR SELECT USING (status = 'active' AND is_confidential = FALSE);

-- =====================================================
-- STORAGE BUCKET SETUP (Run in Supabase Dashboard)
-- =====================================================
-- Create storage bucket for media files:
-- INSERT INTO storage.buckets (id, name, public) VALUES ('media-vault', 'media-vault', true);

-- Storage policies (run in Supabase Dashboard):
-- CREATE POLICY "Public can view media files" ON storage.objects FOR SELECT USING (bucket_id = 'media-vault');
-- CREATE POLICY "Service can upload media files" ON storage.objects FOR INSERT WITH CHECK (bucket_id = 'media-vault' AND auth.role() = 'service_role');
-- CREATE POLICY "Service can update media files" ON storage.objects FOR UPDATE USING (bucket_id = 'media-vault' AND auth.role() = 'service_role');
-- CREATE POLICY "Service can delete media files" ON storage.objects FOR DELETE USING (bucket_id = 'media-vault' AND auth.role() = 'service_role');

-- =====================================================
-- SAMPLE DATA (Optional - for testing)
-- =====================================================
-- INSERT INTO media_videos (title, description, category, file_url, thumbnail_url, duration_seconds, source) VALUES
-- ('Rally Highlights 2024', 'Key moments from the national rally', 'short_clips', 'https://example.com/video1.mp4', 'https://example.com/thumb1.jpg', 180, 'Official Recording'),
-- ('Movement Documentary', 'The complete story of our movement', 'documentaries', 'https://example.com/video2.mp4', 'https://example.com/thumb2.jpg', 3600, 'Documentary Team'),
-- ('Presidential Address', 'Address to the nation', 'public_addresses', 'https://example.com/video3.mp4', 'https://example.com/thumb3.jpg', 1200, 'State House');

-- INSERT INTO media_audio (title, description, category, file_url, speaker, source) VALUES
-- ('Exclusive Interview', 'One-on-one interview with the leader', 'interviews', 'https://example.com/audio1.mp3', 'John Doe', 'Radio Station'),
-- ('Official Statement', 'Statement on recent developments', 'statements', 'https://example.com/audio2.mp3', 'Spokesperson', 'Press Office');

-- INSERT INTO media_images (title, description, category, file_url, thumbnail_url, source) VALUES
-- ('Evidence Photo 1', 'Documented evidence from event', 'evidence', 'https://example.com/img1.jpg', 'https://example.com/img1_thumb.jpg', 'Field Team'),
-- ('Campaign Poster', 'Official campaign visual', 'campaign_visuals', 'https://example.com/img2.jpg', 'https://example.com/img2_thumb.jpg', 'Design Team');

-- INSERT INTO media_documents (title, description, category, file_url, author, source) VALUES
-- ('Annual Report 2024', 'Comprehensive annual report', 'reports', 'https://example.com/doc1.pdf', 'Research Team', 'Internal'),
-- ('Policy Document', 'Official policy guidelines', 'pdfs', 'https://example.com/doc2.pdf', 'Policy Unit', 'Internal'),
-- ('Official Letter', 'Correspondence with government', 'official_letters', 'https://example.com/doc3.pdf', 'Secretary', 'Official');
