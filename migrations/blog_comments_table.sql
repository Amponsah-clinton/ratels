-- =====================================================
-- RATEL MOVEMENT - BLOG COMMENTS & LIKES (Supabase)
-- Run this SQL in your Supabase SQL Editor
-- Threaded comments (YouTube-style) + like per comment
-- =====================================================

-- =====================================================
-- 1. BLOG COMMENTS (threaded: parent_id = null for top-level, else reply)
-- =====================================================
CREATE TABLE IF NOT EXISTS public.blog_comments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    blog_id UUID NOT NULL REFERENCES public.blogs(id) ON DELETE CASCADE,
    parent_id UUID REFERENCES public.blog_comments(id) ON DELETE CASCADE,
    author_name VARCHAR(255) NOT NULL,
    author_email VARCHAR(255),
    body TEXT NOT NULL,
    like_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_blog_comments_blog_id ON public.blog_comments(blog_id);
CREATE INDEX IF NOT EXISTS idx_blog_comments_parent_id ON public.blog_comments(parent_id);
CREATE INDEX IF NOT EXISTS idx_blog_comments_created_at ON public.blog_comments(created_at DESC);

-- Allow public read for published blogs' comments
ALTER TABLE public.blog_comments ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Allow public read blog comments" ON public.blog_comments;
CREATE POLICY "Allow public read blog comments" ON public.blog_comments
    FOR SELECT USING (true);

DROP POLICY IF EXISTS "Allow insert blog comments" ON public.blog_comments;
CREATE POLICY "Allow insert blog comments" ON public.blog_comments
    FOR INSERT WITH CHECK (true);

DROP POLICY IF EXISTS "Allow service role full access blog_comments" ON public.blog_comments;
CREATE POLICY "Allow service role full access blog_comments" ON public.blog_comments
    FOR ALL USING (auth.role() = 'service_role');

-- Trigger: update updated_at
CREATE OR REPLACE FUNCTION update_blog_comments_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_blog_comments_updated_at ON public.blog_comments;
CREATE TRIGGER update_blog_comments_updated_at
    BEFORE UPDATE ON public.blog_comments
    FOR EACH ROW
    EXECUTE FUNCTION update_blog_comments_timestamp();

-- =====================================================
-- 2. BLOG COMMENT LIKES (one like per visitor per comment)
-- =====================================================
CREATE TABLE IF NOT EXISTS public.blog_comment_likes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    comment_id UUID NOT NULL REFERENCES public.blog_comments(id) ON DELETE CASCADE,
    visitor_fingerprint VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(comment_id, visitor_fingerprint)
);

CREATE INDEX IF NOT EXISTS idx_blog_comment_likes_comment_id ON public.blog_comment_likes(comment_id);
CREATE INDEX IF NOT EXISTS idx_blog_comment_likes_fingerprint ON public.blog_comment_likes(visitor_fingerprint);

ALTER TABLE public.blog_comment_likes ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Allow public read blog comment likes" ON public.blog_comment_likes;
CREATE POLICY "Allow public read blog comment likes" ON public.blog_comment_likes
    FOR SELECT USING (true);

DROP POLICY IF EXISTS "Allow insert blog comment like" ON public.blog_comment_likes;
CREATE POLICY "Allow insert blog comment like" ON public.blog_comment_likes
    FOR INSERT WITH CHECK (true);

DROP POLICY IF EXISTS "Allow delete own like" ON public.blog_comment_likes;
CREATE POLICY "Allow delete own like" ON public.blog_comment_likes
    FOR DELETE USING (true);

DROP POLICY IF EXISTS "Allow service role full access blog_comment_likes" ON public.blog_comment_likes;
CREATE POLICY "Allow service role full access blog_comment_likes" ON public.blog_comment_likes
    FOR ALL USING (auth.role() = 'service_role');

-- =====================================================
-- 3. OPTIONAL: Keep like_count in sync (increment/decrement on like/unlike)
-- Application can do: when inserting like -> UPDATE blog_comments SET like_count = like_count + 1;
-- When deleting like -> UPDATE blog_comments SET like_count = like_count - 1;
-- Or use this trigger (increment only on INSERT into blog_comment_likes):
-- =====================================================
CREATE OR REPLACE FUNCTION sync_blog_comment_like_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE public.blog_comments SET like_count = like_count + 1 WHERE id = NEW.comment_id;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE public.blog_comments SET like_count = GREATEST(0, like_count - 1) WHERE id = OLD.comment_id;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS after_blog_comment_like_insert ON public.blog_comment_likes;
CREATE TRIGGER after_blog_comment_like_insert
    AFTER INSERT ON public.blog_comment_likes
    FOR EACH ROW
    EXECUTE FUNCTION sync_blog_comment_like_count();

DROP TRIGGER IF EXISTS after_blog_comment_like_delete ON public.blog_comment_likes;
CREATE TRIGGER after_blog_comment_like_delete
    AFTER DELETE ON public.blog_comment_likes
    FOR EACH ROW
    EXECUTE FUNCTION sync_blog_comment_like_count();
