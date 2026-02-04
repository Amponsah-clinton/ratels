-- =====================================================
-- RATEL MOVEMENT - DONATIONS (Supabase)
-- Run this SQL in your Supabase SQL Editor
-- Stores one-time donations (Paystack); dashboard payments tab shows these
-- =====================================================

CREATE TABLE IF NOT EXISTS public.donations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    amount DECIMAL(12, 2) NOT NULL,
    currency VARCHAR(10) DEFAULT 'GHS',
    is_anonymous BOOLEAN DEFAULT true,
    donor_name VARCHAR(255),
    donor_email VARCHAR(255),
    payment_reference VARCHAR(255) NOT NULL,
    payment_method VARCHAR(50) DEFAULT 'paystack',
    status VARCHAR(50) DEFAULT 'success',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_donations_created_at ON public.donations(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_donations_payment_reference ON public.donations(payment_reference);

ALTER TABLE public.donations ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Service role full access donations" ON public.donations;
CREATE POLICY "Service role full access donations" ON public.donations
    FOR ALL USING (auth.role() = 'service_role');
