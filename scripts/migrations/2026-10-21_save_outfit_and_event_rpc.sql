-- ==============================================================================
-- Forward-Only Migration: Atomic Save Outfit and Style DNA Event RPC
-- Date: 2026-10-21
--
-- Description:
-- 1. Deduplicates any past duplicate save events (keeping the earliest).
-- 2. Adds a partial unique index on public.outfit_events(user_id, outfit_id)
--    where event_type = 'save' to enforce at the DB level that a user has at most
--    one save event per outfit.
-- 3. Creates public.save_outfit_with_event function to atomically update outfit
--    saved status and tags, and record the Style DNA save event in a single
--    transaction with row locking (SELECT ... FOR UPDATE) to serialize concurrent saves.
--
-- Safety Guarantees:
-- - Forward-only and additive.
-- - security invoker preserves PostgreSQL Row Level Security (RLS) under auth.uid().
-- - If either the outfit update or the event insert fails, the transaction rolls back.
-- ==============================================================================

-- 1. Clean up any historical duplicate save events before creating the unique index
-- Uses a deterministic tie-breaker (created_at ASC NULLS LAST, id ASC) so exact timestamp ties or nulls cannot survive
DELETE FROM public.outfit_events
WHERE id IN (
  SELECT id
  FROM (
    SELECT id,
           ROW_NUMBER() OVER (
             PARTITION BY user_id, outfit_id
             ORDER BY created_at ASC NULLS LAST, id ASC
           ) AS rn
    FROM public.outfit_events
    WHERE event_type = 'save'
  ) ranked
  WHERE ranked.rn > 1
);

-- 2. Enforce database-level uniqueness for save events per outfit
CREATE UNIQUE INDEX IF NOT EXISTS idx_outfit_events_user_outfit_save
  ON public.outfit_events (user_id, outfit_id)
  WHERE event_type = 'save';

-- 3. Atomic RPC for saving outfit and recording save event
CREATE OR REPLACE FUNCTION public.save_outfit_with_event(
  p_outfit_id uuid,
  p_tags text[],
  p_event_metadata jsonb DEFAULT '{}'::jsonb
) RETURNS jsonb
LANGUAGE plpgsql
SECURITY INVOKER
AS $$
DECLARE
  v_outfit record;
  v_event_exists boolean;
  v_event_id uuid := null;
  v_created_event boolean := false;
BEGIN
  -- 1. Lock and verify outfit ownership under RLS
  SELECT id, is_saved, tags
  INTO v_outfit
  FROM public.outfits
  WHERE id = p_outfit_id AND user_id = auth.uid()
  FOR UPDATE;

  IF NOT FOUND THEN
    RAISE EXCEPTION 'OUTFIT_NOT_FOUND' USING ERRCODE = 'P0002';
  END IF;

  -- 2. Update outfit is_saved and tags
  UPDATE public.outfits
  SET is_saved = true,
      tags = coalesce(p_tags, '{}'::text[]),
      updated_at = now()
  WHERE id = p_outfit_id AND user_id = auth.uid();

  -- 3. Check for existing save event
  SELECT EXISTS (
    SELECT 1 FROM public.outfit_events
    WHERE user_id = auth.uid()
      AND outfit_id = p_outfit_id
      AND event_type = 'save'
  ) INTO v_event_exists;

  IF NOT v_event_exists THEN
    INSERT INTO public.outfit_events (
      id,
      user_id,
      outfit_id,
      event_type,
      metadata,
      created_at
    ) VALUES (
      gen_random_uuid(),
      auth.uid(),
      p_outfit_id,
      'save',
      coalesce(p_event_metadata, '{}'::jsonb),
      now()
    ) RETURNING id INTO v_event_id;
    v_created_event := true;
  END IF;

  RETURN jsonb_build_object(
    'success', true,
    'outfit_id', p_outfit_id,
    'is_saved', true,
    'tags', coalesce(p_tags, '{}'::text[]),
    'event_created', v_created_event
  );
END;
$$;

GRANT EXECUTE ON FUNCTION public.save_outfit_with_event(uuid, text[], jsonb) TO authenticated;
GRANT EXECUTE ON FUNCTION public.save_outfit_with_event(uuid, text[], jsonb) TO service_role;
