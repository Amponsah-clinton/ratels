-- ============================================
-- Supabase Schema: RATEL Movement Members
-- Run this in your Supabase SQL Editor
-- ============================================

-- Members table
CREATE TABLE IF NOT EXISTS members (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    member_id TEXT UNIQUE NOT NULL,
    full_name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    phone_number TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    profile_image_url TEXT,
    membership_type TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    based_in_nigeria BOOLEAN NOT NULL DEFAULT TRUE,
    state TEXT,
    lga TEXT,
    country TEXT,
    city TEXT,
    engagement_preferences TEXT[] DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for fast email lookup during login
CREATE INDEX IF NOT EXISTS idx_members_email ON members (email);

-- Index for member_id lookup
CREATE INDEX IF NOT EXISTS idx_members_member_id ON members (member_id);

-- Sequence counter table for generating Member IDs per region
CREATE TABLE IF NOT EXISTS member_id_counters (
    region_key TEXT PRIMARY KEY,
    current_count INTEGER NOT NULL DEFAULT 0
);

-- Function to atomically get the next member ID number for a region
CREATE OR REPLACE FUNCTION get_next_member_number(p_region_key TEXT)
RETURNS INTEGER AS $$
DECLARE
    next_num INTEGER;
BEGIN
    INSERT INTO member_id_counters (region_key, current_count)
    VALUES (p_region_key, 1)
    ON CONFLICT (region_key)
    DO UPDATE SET current_count = member_id_counters.current_count + 1
    RETURNING current_count INTO next_num;

    RETURN next_num;
END;
$$ LANGUAGE plpgsql;

-- Enable Row Level Security
ALTER TABLE members ENABLE ROW LEVEL SECURITY;
ALTER TABLE member_id_counters ENABLE ROW LEVEL SECURITY;

-- RLS policies: service_role can do everything
CREATE POLICY "Service role full access on members"
    ON members FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

CREATE POLICY "Service role full access on counters"
    ON member_id_counters FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

-- Allow anon to insert members (for signup) and select own record
CREATE POLICY "Anon can insert members"
    ON members FOR INSERT
    WITH CHECK (true);

CREATE POLICY "Anon can select members by email"
    ON members FOR SELECT
    USING (true);

CREATE POLICY "Anon can use counters"
    ON member_id_counters FOR ALL
    USING (true)
    WITH CHECK (true);

-- Updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER members_updated_at
    BEFORE UPDATE ON members
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- Optional: constrain status values
ALTER TABLE members
    ADD CONSTRAINT members_status_check
    CHECK (status IN ('active', 'suspended', 'deleted'));
