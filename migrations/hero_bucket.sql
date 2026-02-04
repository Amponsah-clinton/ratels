-- =====================================================
-- RATEL MOVEMENT - HERO STORAGE BUCKET
-- Run this in Supabase SQL Editor if you use hero video on the landing page.
-- =====================================================
-- Creates a public "hero" bucket for the landing hero video upload.
-- Dashboard: Site Settings > Hero section > 1 video (autoplay) > Upload video.

INSERT INTO storage.buckets (id, name, public)
VALUES ('hero', 'hero', true)
ON CONFLICT (id) DO UPDATE SET public = true;
