-- =====================================================
-- RATEL MOVEMENT - LEADERSHIP TABLES
-- Run this SQL in your Supabase SQL Editor
-- =====================================================

-- 1. FOUNDING VISION TABLE
CREATE TABLE IF NOT EXISTS public.founding_vision (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    display_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. LEADERSHIP COUNCIL TABLE
CREATE TABLE IF NOT EXISTS public.leadership_council (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    full_name VARCHAR(255) NOT NULL,
    position VARCHAR(255) NOT NULL,
    bio TEXT,
    profile_image_url TEXT,
    email VARCHAR(255),
    phone VARCHAR(50),
    linkedin_url TEXT,
    twitter_url TEXT,
    display_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. STRATEGIC COMMITTEES TABLE
CREATE TABLE IF NOT EXISTS public.strategic_committees (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    committee_name VARCHAR(255) NOT NULL,
    description TEXT,
    chairperson VARCHAR(255),
    members TEXT[], -- Array of member names
    responsibilities TEXT[],
    profile_image_url TEXT,
    display_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. ADVISORY VOICES TABLE
CREATE TABLE IF NOT EXISTS public.advisory_voices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    full_name VARCHAR(255) NOT NULL,
    title VARCHAR(255),
    organization VARCHAR(255),
    expertise TEXT,
    bio TEXT,
    profile_image_url TEXT,
    quote TEXT,
    display_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. CODE OF CONDUCT TABLE
CREATE TABLE IF NOT EXISTS public.code_of_conduct (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    section_title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    icon VARCHAR(50), -- Icon name for display
    display_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- =====================================================
-- INDEXES FOR BETTER PERFORMANCE
-- =====================================================

CREATE INDEX IF NOT EXISTS idx_founding_vision_order ON public.founding_vision(display_order);
CREATE INDEX IF NOT EXISTS idx_founding_vision_active ON public.founding_vision(is_active);

CREATE INDEX IF NOT EXISTS idx_leadership_council_order ON public.leadership_council(display_order);
CREATE INDEX IF NOT EXISTS idx_leadership_council_active ON public.leadership_council(is_active);

CREATE INDEX IF NOT EXISTS idx_strategic_committees_order ON public.strategic_committees(display_order);
CREATE INDEX IF NOT EXISTS idx_strategic_committees_active ON public.strategic_committees(is_active);

CREATE INDEX IF NOT EXISTS idx_advisory_voices_order ON public.advisory_voices(display_order);
CREATE INDEX IF NOT EXISTS idx_advisory_voices_active ON public.advisory_voices(is_active);

CREATE INDEX IF NOT EXISTS idx_code_of_conduct_order ON public.code_of_conduct(display_order);
CREATE INDEX IF NOT EXISTS idx_code_of_conduct_active ON public.code_of_conduct(is_active);

-- =====================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- =====================================================

-- Enable RLS on all tables
ALTER TABLE public.founding_vision ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.leadership_council ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.strategic_committees ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.advisory_voices ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.code_of_conduct ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist (safe to re-run)
DROP POLICY IF EXISTS "Allow public read founding_vision" ON public.founding_vision;
DROP POLICY IF EXISTS "Allow public read leadership_council" ON public.leadership_council;
DROP POLICY IF EXISTS "Allow public read strategic_committees" ON public.strategic_committees;
DROP POLICY IF EXISTS "Allow public read advisory_voices" ON public.advisory_voices;
DROP POLICY IF EXISTS "Allow public read code_of_conduct" ON public.code_of_conduct;

DROP POLICY IF EXISTS "Allow service role full access founding_vision" ON public.founding_vision;
DROP POLICY IF EXISTS "Allow service role full access leadership_council" ON public.leadership_council;
DROP POLICY IF EXISTS "Allow service role full access strategic_committees" ON public.strategic_committees;
DROP POLICY IF EXISTS "Allow service role full access advisory_voices" ON public.advisory_voices;
DROP POLICY IF EXISTS "Allow service role full access code_of_conduct" ON public.code_of_conduct;

-- Allow public read access for active records
CREATE POLICY "Allow public read founding_vision" ON public.founding_vision
    FOR SELECT USING (is_active = true);

CREATE POLICY "Allow public read leadership_council" ON public.leadership_council
    FOR SELECT USING (is_active = true);

CREATE POLICY "Allow public read strategic_committees" ON public.strategic_committees
    FOR SELECT USING (is_active = true);

CREATE POLICY "Allow public read advisory_voices" ON public.advisory_voices
    FOR SELECT USING (is_active = true);

CREATE POLICY "Allow public read code_of_conduct" ON public.code_of_conduct
    FOR SELECT USING (is_active = true);

-- Allow service role full access
CREATE POLICY "Allow service role full access founding_vision" ON public.founding_vision
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Allow service role full access leadership_council" ON public.leadership_council
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Allow service role full access strategic_committees" ON public.strategic_committees
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Allow service role full access advisory_voices" ON public.advisory_voices
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Allow service role full access code_of_conduct" ON public.code_of_conduct
    FOR ALL USING (auth.role() = 'service_role');

-- =====================================================
-- SAMPLE DATA (Optional - Comment out in production)
-- Only inserts if tables are empty
-- =====================================================

-- Sample Founding Vision (only if table is empty)
INSERT INTO public.founding_vision (title, content, display_order)
SELECT 'Our Beginning', 'The RATEL Movement was born from a collective frustration with systemic injustice and a shared belief that silence in the face of wrongdoing is complicity. Our founders recognized that meaningful change requires organized, persistent, and courageous action.', 1
WHERE NOT EXISTS (SELECT 1 FROM public.founding_vision LIMIT 1);

INSERT INTO public.founding_vision (title, content, display_order)
SELECT 'Core Belief', 'We believe that every individual has both the right and responsibility to demand accountability from those in power. This is not merely activism—it is citizenship in its truest form.', 2
WHERE NOT EXISTS (SELECT 1 FROM public.founding_vision WHERE title = 'Core Belief');

INSERT INTO public.founding_vision (title, content, display_order)
SELECT 'The Path Forward', 'Our vision extends beyond protest to transformation. We seek to build systems of accountability, educate communities, and empower individuals to become agents of change in their own spheres of influence.', 3
WHERE NOT EXISTS (SELECT 1 FROM public.founding_vision WHERE title = 'The Path Forward');

-- Sample Leadership Council (only if table is empty)
INSERT INTO public.leadership_council (full_name, position, bio, display_order)
SELECT 'Dr. Amara Okonkwo', 'National Coordinator', 'A veteran human rights advocate with over 15 years of experience in civil society organization and community mobilization.', 1
WHERE NOT EXISTS (SELECT 1 FROM public.leadership_council LIMIT 1);

INSERT INTO public.leadership_council (full_name, position, bio, display_order)
SELECT 'Barrister Chukwuma Eze', 'Legal Director', 'A constitutional lawyer specializing in human rights law and public interest litigation.', 2
WHERE NOT EXISTS (SELECT 1 FROM public.leadership_council WHERE full_name = 'Barrister Chukwuma Eze');

INSERT INTO public.leadership_council (full_name, position, bio, display_order)
SELECT 'Fatima Hassan', 'Director of Communications', 'An award-winning journalist and media strategist committed to amplifying marginalized voices.', 3
WHERE NOT EXISTS (SELECT 1 FROM public.leadership_council WHERE full_name = 'Fatima Hassan');

-- Sample Strategic Committees (only if table is empty)
INSERT INTO public.strategic_committees (committee_name, description, chairperson, responsibilities, display_order)
SELECT 'Legal Affairs Committee', 'Handles all legal matters, advocacy strategies, and policy recommendations.', 'Barrister Chukwuma Eze', ARRAY['Legal research and documentation', 'Policy advocacy', 'Member legal support'], 1
WHERE NOT EXISTS (SELECT 1 FROM public.strategic_committees LIMIT 1);

INSERT INTO public.strategic_committees (committee_name, description, chairperson, responsibilities, display_order)
SELECT 'Mobilization Committee', 'Coordinates grassroots organizing, member recruitment, and community engagement.', 'Aisha Mohammed', ARRAY['Community outreach', 'Member recruitment', 'Event coordination'], 2
WHERE NOT EXISTS (SELECT 1 FROM public.strategic_committees WHERE committee_name = 'Mobilization Committee');

INSERT INTO public.strategic_committees (committee_name, description, chairperson, responsibilities, display_order)
SELECT 'Media & Communications', 'Manages public relations, social media, and documentary evidence.', 'Fatima Hassan', ARRAY['Media relations', 'Content creation', 'Evidence documentation'], 3
WHERE NOT EXISTS (SELECT 1 FROM public.strategic_committees WHERE committee_name = 'Media & Communications');

-- Sample Advisory Voices (only if table is empty)
INSERT INTO public.advisory_voices (full_name, title, organization, expertise, quote, display_order)
SELECT 'Prof. Ngozi Adichie', 'Distinguished Advisor', 'University of Lagos', 'Constitutional Law & Human Rights', 'The measure of a society is how it treats its most vulnerable members.', 1
WHERE NOT EXISTS (SELECT 1 FROM public.advisory_voices LIMIT 1);

INSERT INTO public.advisory_voices (full_name, title, organization, expertise, quote, display_order)
SELECT 'Dr. Yusuf Ibrahim', 'Senior Advisor', 'African Democracy Institute', 'Democratic Governance', 'Democracy is not a spectator sport—it demands active participation.', 2
WHERE NOT EXISTS (SELECT 1 FROM public.advisory_voices WHERE full_name = 'Dr. Yusuf Ibrahim');

-- Sample Code of Conduct (only if table is empty)
INSERT INTO public.code_of_conduct (section_title, content, icon, display_order)
SELECT 'Integrity', 'Members shall conduct themselves with honesty and transparency in all movement activities. We do not fabricate evidence, spread misinformation, or engage in deceptive practices.', 'shield', 1
WHERE NOT EXISTS (SELECT 1 FROM public.code_of_conduct LIMIT 1);

INSERT INTO public.code_of_conduct (section_title, content, icon, display_order)
SELECT 'Non-Violence', 'The RATEL Movement is committed to peaceful advocacy. Violence, whether physical or verbal, has no place in our organization.', 'heart', 2
WHERE NOT EXISTS (SELECT 1 FROM public.code_of_conduct WHERE section_title = 'Non-Violence');

INSERT INTO public.code_of_conduct (section_title, content, icon, display_order)
SELECT 'Respect', 'We treat all individuals with dignity and respect, regardless of their position or affiliation. Constructive dialogue, not personal attacks, drives our engagement.', 'users', 3
WHERE NOT EXISTS (SELECT 1 FROM public.code_of_conduct WHERE section_title = 'Respect');

INSERT INTO public.code_of_conduct (section_title, content, icon, display_order)
SELECT 'Accountability', 'We hold ourselves to the same standards we demand of others. Members are accountable for their actions and must report any violations of this code.', 'check-circle', 4
WHERE NOT EXISTS (SELECT 1 FROM public.code_of_conduct WHERE section_title = 'Accountability');

INSERT INTO public.code_of_conduct (section_title, content, icon, display_order)
SELECT 'Confidentiality', 'Sensitive information shared within the movement must be protected. Member privacy and operational security are paramount.', 'lock', 5
WHERE NOT EXISTS (SELECT 1 FROM public.code_of_conduct WHERE section_title = 'Confidentiality');

-- =====================================================
-- ADD PROFILE IMAGE URL TO STRATEGIC COMMITTEES
-- Run this if the table already exists without the field
-- =====================================================
ALTER TABLE public.strategic_committees 
ADD COLUMN IF NOT EXISTS profile_image_url TEXT;
