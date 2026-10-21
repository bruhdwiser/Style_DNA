-- ==============================================================================
-- Forward-Only Migration: Add Tags to Outfits for Saved Looks
-- Date: 2026-10-21
--
-- Description:
-- Adds a tags array column to public.outfits and a GIN index for fast filtering
-- by tags (e.g., Work, Date Night, Wedding, Vacation, Try Later).
--
-- Safety Guarantees:
-- - Forward-only and additive (ADD COLUMN IF NOT EXISTS).
-- - Row Level Security on public.outfits automatically covers the new column.
-- - Defaults to '{}'::text[] so existing rows are unaffected and never null.
-- ==============================================================================

ALTER TABLE public.outfits
  ADD COLUMN IF NOT EXISTS tags text[] NOT NULL DEFAULT '{}';

CREATE INDEX IF NOT EXISTS idx_outfits_user_saved_tags
  ON public.outfits USING gin (tags);

COMMENT ON COLUMN public.outfits.tags IS 'User-assigned classification tags for saved looks (e.g. Work, Date Night, Wedding, Vacation, Try Later).';
