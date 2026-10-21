-- ==============================================================================
-- Forward-Only Migration: Atomic Save Outfit RPC (Phase 2)
-- Date: 2026-10-21
--
-- Description:
-- Creates public.save_outfit_with_items function to atomically persist an outfit
-- and its slot item references in a single ACID transaction under Row Level Security.
--
-- Safety Guarantees:
-- - Forward-only and additive (CREATE OR REPLACE FUNCTION).
-- - security invoker preserves PostgreSQL Row Level Security (RLS) under auth.uid().
-- - If any item insert fails, the outfit row is rolled back automatically.
-- ==============================================================================

create or replace function public.save_outfit_with_items(
  p_outfit jsonb,
  p_items jsonb
) returns uuid
language plpgsql
security invoker
as $$
declare
  v_outfit_id uuid;
begin
  insert into public.outfits (
    id,
    user_id,
    occasion,
    vibe,
    skeleton,
    score,
    component_scores,
    reasons,
    wardrobe_only,
    is_saved,
    metadata,
    created_at,
    updated_at
  ) values (
    (p_outfit->>'id')::uuid,
    auth.uid(),
    p_outfit->>'occasion',
    p_outfit->>'vibe',
    p_outfit->>'skeleton',
    (p_outfit->>'score')::numeric,
    coalesce(p_outfit->'component_scores', '{}'::jsonb),
    coalesce((select array_agg(x) from jsonb_array_elements_text(p_outfit->'reasons') t(x)), '{}'::text[]),
    coalesce((p_outfit->>'wardrobe_only')::boolean, true),
    false,
    coalesce(p_outfit->'metadata', '{}'::jsonb),
    coalesce((p_outfit->>'created_at')::timestamptz, now()),
    coalesce((p_outfit->>'updated_at')::timestamptz, now())
  ) returning id into v_outfit_id;

  if p_items is not null and jsonb_array_length(p_items) > 0 then
    insert into public.outfit_items (
      outfit_id,
      user_id,
      slot,
      source_type,
      wardrobe_item_id,
      product_id,
      created_at
    )
    select
      v_outfit_id,
      auth.uid(),
      item->>'slot',
      coalesce(item->>'source_type', 'wardrobe'),
      case when (item->>'wardrobe_item_id') is not null and (item->>'wardrobe_item_id') <> '' then (item->>'wardrobe_item_id')::uuid else null end,
      case when (item->>'product_id') is not null and (item->>'product_id') <> '' then (item->>'product_id')::uuid else null end,
      coalesce((item->>'created_at')::timestamptz, now())
    from jsonb_array_elements(p_items) as item;
  end if;

  return v_outfit_id;
end;
$$;

grant execute on function public.save_outfit_with_items(jsonb, jsonb) to authenticated;
grant execute on function public.save_outfit_with_items(jsonb, jsonb) to service_role;
