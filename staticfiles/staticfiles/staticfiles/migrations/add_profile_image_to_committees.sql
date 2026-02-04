-- =====================================================
-- ADD PROFILE IMAGE URL TO STRATEGIC COMMITTEES
-- Run this SQL in your Supabase SQL Editor
-- =====================================================

-- Add profile_image_url column to strategic_committees table if it doesn't exist
ALTER TABLE public.strategic_committees 
ADD COLUMN IF NOT EXISTS profile_image_url TEXT;

-- Note: Make sure you have created the "leadership" storage bucket in Supabase
-- Storage > Buckets > New Bucket
-- Name: leadership
-- Public: Yes (if you want public access to images)
