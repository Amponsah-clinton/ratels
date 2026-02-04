-- =====================================================
-- RATEL MOVEMENT - CONTACT INQUIRIES TABLE
-- Run this SQL in your Supabase SQL Editor
-- =====================================================

-- Contact Inquiries Table
CREATE TABLE IF NOT EXISTS public.contact_inquiries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Inquiry Type: 'general', 'media', 'secure_tip', 'encrypted'
    inquiry_type VARCHAR(50) NOT NULL DEFAULT 'general',

    -- Common Fields
    subject VARCHAR(500),
    message TEXT NOT NULL,

    -- Contact Information (optional for anonymous tips)
    full_name VARCHAR(255),
    email VARCHAR(255),
    phone VARCHAR(50),
    organization VARCHAR(255),  -- For media inquiries

    -- Media-specific fields
    media_outlet VARCHAR(255),
    deadline TIMESTAMPTZ,
    story_type VARCHAR(100),  -- 'interview', 'statement', 'background', 'other'

    -- Secure tip fields
    is_anonymous BOOLEAN DEFAULT false,
    tip_reference_code VARCHAR(50),  -- For anonymous follow-up
    urgency_level VARCHAR(20) DEFAULT 'normal',  -- 'low', 'normal', 'high', 'critical'
    evidence_description TEXT,

    -- Encrypted contact fields
    pgp_public_key TEXT,
    preferred_secure_channel VARCHAR(100),  -- 'signal', 'protonmail', 'session', 'other'
    secure_contact_handle VARCHAR(255),

    -- Status and tracking
    status VARCHAR(50) DEFAULT 'new',  -- 'new', 'in_progress', 'replied', 'resolved', 'archived'
    priority VARCHAR(20) DEFAULT 'normal',  -- 'low', 'normal', 'high', 'urgent'
    assigned_to VARCHAR(255),

    -- Admin notes (internal)
    internal_notes TEXT,

    -- Reply tracking
    replied_at TIMESTAMPTZ,
    replied_by VARCHAR(255),
    reply_message TEXT,

    -- Metadata
    ip_address VARCHAR(45),
    user_agent TEXT,
    source_page VARCHAR(255),

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_contact_inquiries_type ON public.contact_inquiries(inquiry_type);
CREATE INDEX IF NOT EXISTS idx_contact_inquiries_status ON public.contact_inquiries(status);
CREATE INDEX IF NOT EXISTS idx_contact_inquiries_priority ON public.contact_inquiries(priority);
CREATE INDEX IF NOT EXISTS idx_contact_inquiries_created ON public.contact_inquiries(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_contact_inquiries_email ON public.contact_inquiries(email);
CREATE INDEX IF NOT EXISTS idx_contact_inquiries_reference ON public.contact_inquiries(tip_reference_code);

-- Enable Row Level Security
ALTER TABLE public.contact_inquiries ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist (safe to re-run)
DROP POLICY IF EXISTS "Allow public insert contact_inquiries" ON public.contact_inquiries;
DROP POLICY IF EXISTS "Allow service role full access contact_inquiries" ON public.contact_inquiries;

-- Allow public to submit inquiries (insert only)
CREATE POLICY "Allow public insert contact_inquiries" ON public.contact_inquiries
    FOR INSERT WITH CHECK (true);

-- Allow service role full access (for admin dashboard)
CREATE POLICY "Allow service role full access contact_inquiries" ON public.contact_inquiries
    FOR ALL USING (auth.role() = 'service_role');

-- Function to generate unique reference code for anonymous tips
CREATE OR REPLACE FUNCTION generate_tip_reference()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.is_anonymous = true AND NEW.tip_reference_code IS NULL THEN
        NEW.tip_reference_code := 'TIP-' || UPPER(SUBSTRING(MD5(RANDOM()::TEXT) FROM 1 FOR 8));
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Drop trigger if exists
DROP TRIGGER IF EXISTS set_tip_reference ON public.contact_inquiries;

-- Trigger to auto-generate reference code
CREATE TRIGGER set_tip_reference
    BEFORE INSERT ON public.contact_inquiries
    FOR EACH ROW
    EXECUTE FUNCTION generate_tip_reference();

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_contact_inquiries_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Drop trigger if exists
DROP TRIGGER IF EXISTS update_contact_inquiries_updated_at ON public.contact_inquiries;

-- Trigger to auto-update timestamp
CREATE TRIGGER update_contact_inquiries_updated_at
    BEFORE UPDATE ON public.contact_inquiries
    FOR EACH ROW
    EXECUTE FUNCTION update_contact_inquiries_timestamp();
