-- ==============================================================================
-- Migration: Add outfit events and Style DNA tracking
-- Run eighth, after add-outfits-and-saved-looks.sql.
-- Date: 2026-10-12
-- Forward-only, additive migration.
-- Tracks like, dislike, save, skip, and wear interactions on outfits.
-- Owner-scoped RLS guarantees complete isolation between users.
-- ==============================================================================

CREATE TABLE IF NOT EXISTS public.outfit_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    outfit_id UUID NOT NULL REFERENCES public.outfits(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL CHECK (event_type IN ('like', 'dislike', 'save', 'skip', 'wear')),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

-- Indexes for rapid affinity computation and lookup
CREATE INDEX IF NOT EXISTS idx_outfit_events_user_created 
    ON public.outfit_events(user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_outfit_events_outfit_id 
    ON public.outfit_events(outfit_id);

CREATE INDEX IF NOT EXISTS idx_outfit_events_user_event 
    ON public.outfit_events(user_id, event_type);

-- Enable Row Level Security
ALTER TABLE public.outfit_events ENABLE ROW LEVEL SECURITY;

-- RLS: Authenticated users can select only their own events
DROP POLICY IF EXISTS "Users can view own outfit events" ON public.outfit_events;
CREATE POLICY "Users can view own outfit events"
    ON public.outfit_events
    FOR SELECT
    TO authenticated
    USING (auth.uid() = user_id);

-- RLS: Authenticated users can record events only under their own user ID
DROP POLICY IF EXISTS "Users can insert own outfit events" ON public.outfit_events;
CREATE POLICY "Users can insert own outfit events"
    ON public.outfit_events
    FOR INSERT
    TO authenticated
    WITH CHECK (auth.uid() = user_id);

-- RLS: Authenticated users can delete only their own events (e.g., Reset Style DNA)
DROP POLICY IF EXISTS "Users can delete own outfit events" ON public.outfit_events;
CREATE POLICY "Users can delete own outfit events"
    ON public.outfit_events
    FOR DELETE
    TO authenticated
    USING (auth.uid() = user_id);

GRANT SELECT, INSERT, DELETE ON public.outfit_events TO authenticated;
GRANT ALL ON public.outfit_events TO service_role;
