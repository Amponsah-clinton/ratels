-- =====================================================
-- RATEL MOVEMENT - PAYSTACK SETTINGS (Supabase)
-- Run this SQL in your Supabase SQL Editor
-- Single row: public_key (for frontend), secret_key (server-only)
-- When set, dashboard site-settings overrides env PAYSTACK_* keys
-- =====================================================

CREATE TABLE IF NOT EXISTS public.paystack_settings (
    id INTEGER PRIMARY KEY DEFAULT 1,
    public_key TEXT DEFAULT '',
    secret_key TEXT DEFAULT '',
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT single_row CHECK (id = 1)
);

-- Ensure exactly one row exists
INSERT INTO public.paystack_settings (id, public_key, secret_key, updated_at)
VALUES (1, '', '', NOW())
ON CONFLICT (id) DO NOTHING;

-- RLS: allow service_role full access (dashboard uses service key)
ALTER TABLE public.paystack_settings ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Service role full access paystack_settings" ON public.paystack_settings;
CREATE POLICY "Service role full access paystack_settings" ON public.paystack_settings
    FOR ALL USING (auth.role() = 'service_role');

-- Optional: allow anon read of public_key only for frontend Paystack Pop
-- (If you prefer public_key to be read via API with anon key, add a view or separate table with only public_key.)
-- Here we use service_role for all reads/writes from the Django app.
