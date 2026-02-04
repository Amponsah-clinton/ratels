-- =====================================================
-- RATEL MOVEMENT - FAQs TABLE
-- Run this SQL in your Supabase SQL Editor
-- =====================================================

-- FAQs Table
CREATE TABLE IF NOT EXISTS public.faqs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Category for grouping
    category VARCHAR(100) DEFAULT 'general',  -- 'general', 'political', 'funding', 'membership', 'security', 'other'

    -- Question and Answer
    question TEXT NOT NULL,
    answer TEXT NOT NULL,

    -- Display settings
    display_order INTEGER DEFAULT 0,
    is_featured BOOLEAN DEFAULT false,  -- Show on homepage or highlight
    is_active BOOLEAN DEFAULT true,

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_faqs_category ON public.faqs(category);
CREATE INDEX IF NOT EXISTS idx_faqs_order ON public.faqs(display_order);
CREATE INDEX IF NOT EXISTS idx_faqs_active ON public.faqs(is_active);
CREATE INDEX IF NOT EXISTS idx_faqs_featured ON public.faqs(is_featured);

-- Enable Row Level Security
ALTER TABLE public.faqs ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist (safe to re-run)
DROP POLICY IF EXISTS "Allow public read faqs" ON public.faqs;
DROP POLICY IF EXISTS "Allow service role full access faqs" ON public.faqs;

-- Allow public to read active FAQs
CREATE POLICY "Allow public read faqs" ON public.faqs
    FOR SELECT USING (is_active = true);

-- Allow service role full access (for admin dashboard)
CREATE POLICY "Allow service role full access faqs" ON public.faqs
    FOR ALL USING (auth.role() = 'service_role');

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_faqs_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Drop trigger if exists
DROP TRIGGER IF EXISTS update_faqs_updated_at ON public.faqs;

-- Trigger to auto-update timestamp
CREATE TRIGGER update_faqs_updated_at
    BEFORE UPDATE ON public.faqs
    FOR EACH ROW
    EXECUTE FUNCTION update_faqs_timestamp();

-- =====================================================
-- SAMPLE DATA (Optional - Pre-empt Hard Questions)
-- =====================================================

INSERT INTO public.faqs (category, question, answer, display_order, is_featured)
SELECT 'political',
       'Is RATEL political?',
       'RATEL is a non-partisan civic movement. We do not endorse, support, or oppose any political party or candidate. Our focus is on accountability, transparency, and good governance regardless of who is in power. We believe that demanding accountability from public officials is a civic duty, not a political act.',
       1, true
WHERE NOT EXISTS (SELECT 1 FROM public.faqs WHERE question = 'Is RATEL political?');

INSERT INTO public.faqs (category, question, answer, display_order, is_featured)
SELECT 'funding',
       'Who funds RATEL?',
       'RATEL is funded entirely by membership dues, voluntary donations from individuals, and occasional grants from transparent civil society organizations. We do not accept funding from political parties, government agencies, or anonymous sources. Our financial records are available for review by members upon request.',
       2, true
WHERE NOT EXISTS (SELECT 1 FROM public.faqs WHERE question = 'Who funds RATEL?');

INSERT INTO public.faqs (category, question, answer, display_order, is_featured)
SELECT 'membership',
       'Are members verified?',
       'Yes. All members undergo a verification process that includes identity confirmation and agreement to our code of conduct. This ensures the integrity of our movement and protects against infiltration by bad actors. Verification details are kept strictly confidential.',
       3, true
WHERE NOT EXISTS (SELECT 1 FROM public.faqs WHERE question = 'Are members verified?');

INSERT INTO public.faqs (category, question, answer, display_order, is_featured)
SELECT 'membership',
       'Is membership public?',
       'No. Member identities are protected and never disclosed publicly without explicit consent. We understand that civic activism can carry risks, and we take member privacy seriously. Only verified leadership has access to membership records, which are stored securely.',
       4, true
WHERE NOT EXISTS (SELECT 1 FROM public.faqs WHERE question = 'Is membership public?');

INSERT INTO public.faqs (category, question, answer, display_order, is_featured)
SELECT 'security',
       'How is data protected?',
       'We employ industry-standard security measures including end-to-end encryption for sensitive communications, secure cloud storage with strict access controls, and regular security audits. We do not sell, share, or monetize member data. Our data protection practices comply with international privacy standards.',
       5, true
WHERE NOT EXISTS (SELECT 1 FROM public.faqs WHERE question = 'How is data protected?');

INSERT INTO public.faqs (category, question, answer, display_order)
SELECT 'general',
       'How can I join RATEL?',
       'You can join RATEL by completing the membership application on our website. The process involves providing basic information, agreeing to our code of conduct, and completing identity verification. Membership is open to all individuals who share our commitment to accountability and good governance.',
       6
WHERE NOT EXISTS (SELECT 1 FROM public.faqs WHERE question = 'How can I join RATEL?');

INSERT INTO public.faqs (category, question, answer, display_order)
SELECT 'general',
       'What does RATEL stand for?',
       'RATEL is inspired by the honey badger (Mellivora capensis), known in some African languages as "ratel." The honey badger is renowned for its fearlessness, tenacity, and refusal to back down - qualities that embody our movement''s approach to demanding accountability.',
       7
WHERE NOT EXISTS (SELECT 1 FROM public.faqs WHERE question = 'What does RATEL stand for?');
