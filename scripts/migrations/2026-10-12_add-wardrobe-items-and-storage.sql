-- ==============================================================================
-- Forward-Only Migration: Wardrobe Items and Private Storage Bucket
-- Date: 2026-10-12
--
-- Description:
-- Creates public.wardrobe_items table with owner-scoped Row Level Security (RLS)
-- and provisions the private Supabase Storage bucket 'wardrobe' with per-user
-- folder access policies.
--
-- Safety Guarantees:
-- - Forward-only and additive (CREATE TABLE IF NOT EXISTS).
-- - Does NOT modify existing products, carts, or profile tables.
-- - RLS enabled: users can only read, insert, update, or delete their own items.
-- - Private storage bucket: files are isolated to auth.uid() folders.
-- ==============================================================================

-- 1. Create public.wardrobe_items table
create table if not exists public.wardrobe_items (
  id             uuid primary key default gen_random_uuid(),
  user_id        uuid not null references auth.users(id) on delete cascade,
  -- Storage paths
  image_url      text not null,                 -- reference path or signed view URL
  storage_path   text not null,                 -- object key in 'wardrobe' bucket: <user_id>/<filename>
  thumbnail_path text,                          -- thumbnail key: <user_id>/<filename>_thumb.jpg
  -- Garment taxonomy & styling attributes
  category       text not null,                 -- top, bottom, dress, saree, ethnic_set, layer, shoes, bag, jewelry
  slot           text not null,                 -- skeleton slot: top, bottom, ethnic_bottom, dress, saree, ethnic_set, layer, shoes, bag, jewelry, dupatta
  sub_category   text,                          -- t-shirt, blouse, kurta, saree, jeans, trousers, sneakers, etc.
  color_tags     text[] default '{}',           -- color names for harmony rules
  primary_color  text,                          -- dominant color name
  fit            text,                          -- slim, regular, relaxed, oversized
  formality      integer default 1 check (formality is null or (formality >= 0 and formality <= 3)),
  occasions      text[] default '{}',           -- casual, work, party, formal, festive, wedding, lounge, college
  seasons        text[] default '{}',           -- summer, winter, monsoon, all_season
  style_tags     text[] default '{}',           -- minimal, classic, streetwear, traditional, bohemian, etc.
  pattern        text default 'solid',          -- solid, floral, striped, printed, plaid
  neckline       text,                          -- v-neck, crew, round, collared
  rise           text,                          -- high, mid, low
  length         text,                          -- crop, regular, midi, maxi, ankle
  notes          text,                          -- user's private notes
  -- Review state
  needs_review   boolean not null default true, -- true when derived tags need user confirmation
  -- Image metadata (dimensions, byte size, format)
  metadata       jsonb default '{}',
  -- Timestamps
  created_at     timestamptz not null default now(),
  updated_at     timestamptz not null default now()
);

-- 2. Indexes for queries
create index if not exists idx_wardrobe_items_user_id
  on public.wardrobe_items(user_id);

create index if not exists idx_wardrobe_items_user_slot
  on public.wardrobe_items(user_id, slot);

create index if not exists idx_wardrobe_items_needs_review
  on public.wardrobe_items(user_id)
  where needs_review = true;

-- 3. Row Level Security on wardrobe_items
alter table public.wardrobe_items enable row level security;

create policy if not exists "Users manage own wardrobe items"
  on public.wardrobe_items for all
  to authenticated
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

-- Documentation comments
comment on table public.wardrobe_items is 'Private digital wardrobe items owned by authenticated users with RLS.';
comment on column public.wardrobe_items.slot is 'Garment slot used by the deterministic outfit skeleton engine.';
comment on column public.wardrobe_items.needs_review is 'True if auto-derived taxonomy attributes have not been confirmed by the user.';
comment on column public.wardrobe_items.storage_path is 'Path to the sanitized image in the private wardrobe storage bucket.';

-- 4. Private Storage Bucket Setup
-- Note: executed in storage schema if permissions allow; idempotent
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('wardrobe', 'wardrobe', false, 10485760, array['image/jpeg', 'image/png', 'image/webp'])
on conflict (id) do update set public = false;

-- 5. Storage RLS Policies: users access only their own user_id folder
create policy if not exists "Users upload to own folder"
  on storage.objects for insert
  to authenticated
  with check (
    bucket_id = 'wardrobe'
    and (storage.foldername(name))[1] = auth.uid()::text
  );

create policy if not exists "Users read own folder"
  on storage.objects for select
  to authenticated
  using (
    bucket_id = 'wardrobe'
    and (storage.foldername(name))[1] = auth.uid()::text
  );

create policy if not exists "Users update own folder"
  on storage.objects for update
  to authenticated
  using (
    bucket_id = 'wardrobe'
    and (storage.foldername(name))[1] = auth.uid()::text
  );

create policy if not exists "Users delete own folder"
  on storage.objects for delete
  to authenticated
  using (
    bucket_id = 'wardrobe'
    and (storage.foldername(name))[1] = auth.uid()::text
  );
