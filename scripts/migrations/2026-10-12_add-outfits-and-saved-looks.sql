-- ==============================================================================
-- Forward-Only Migration: Outfits and Outfit Items (Phase 6)
-- Date: 2026-10-12
--
-- Description:
-- Creates public.outfits and public.outfit_items tables for storing generated
-- and saved outfit combinations with Row Level Security (RLS).
--
-- Safety Guarantees:
-- - Forward-only and additive (CREATE TABLE IF NOT EXISTS).
-- - Does NOT modify existing products, carts, profiles, or wardrobe tables.
-- - RLS enabled: users can only read, insert, update, or delete their own outfits.
-- - Cascading foreign keys on auth.users(id).
-- ==============================================================================

-- 1. Create public.outfits table
create table if not exists public.outfits (
  id               uuid primary key default gen_random_uuid(),
  user_id          uuid not null references auth.users(id) on delete cascade,
  occasion         text not null,                 -- casual, work, party, formal, festive, wedding, lounge, college
  vibe             text,                          -- minimal, classic, bohemian, streetwear, elegant, etc.
  skeleton         text not null,                 -- top_bottom, dress, saree, ethnic_set
  score            numeric(5,3) not null default 0.500,
  component_scores jsonb not null default '{}',   -- {"color": 0.9, "occasion": 0.85, ...}
  reasons          text[] not null default '{}',  -- factual explanation strings
  wardrobe_only    boolean not null default true,
  is_saved         boolean not null default false,
  metadata         jsonb default '{}',
  created_at       timestamptz not null default now(),
  updated_at       timestamptz not null default now()
);

-- 2. Create public.outfit_items table
create table if not exists public.outfit_items (
  id               uuid primary key default gen_random_uuid(),
  outfit_id        uuid not null references public.outfits(id) on delete cascade,
  user_id          uuid not null references auth.users(id) on delete cascade,
  slot             text not null,                 -- top, bottom, dress, saree, shoes, layer, bag, jewelry, dupatta
  source_type      text not null default 'wardrobe', -- 'wardrobe' or 'catalog'
  wardrobe_item_id uuid references public.wardrobe_items(id) on delete set null,
  product_id       uuid references public.products(id) on delete set null,
  created_at       timestamptz not null default now()
);

-- 3. Indexes for fast query performance
create index if not exists idx_outfits_user_saved
  on public.outfits(user_id, is_saved);

create index if not exists idx_outfits_user_created
  on public.outfits(user_id, created_at desc);

create index if not exists idx_outfit_items_outfit
  on public.outfit_items(outfit_id);

create index if not exists idx_outfit_items_user
  on public.outfit_items(user_id);

-- 4. Row Level Security
alter table public.outfits enable row level security;
alter table public.outfit_items enable row level security;

create policy if not exists "Users manage own outfits"
  on public.outfits for all
  to authenticated
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

create policy if not exists "Users manage own outfit items"
  on public.outfit_items for all
  to authenticated
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

-- Documentation comments
comment on table public.outfits is 'Generated and saved outfit recommendations with RLS.';
comment on column public.outfits.score is 'Overall compatibility score from the pure Python rules engine (0.0 to 1.0).';
comment on column public.outfits.reasons is 'Factual explanation strings connecting actual clothing attributes to occasion constraints.';
comment on table public.outfit_items is 'Item mappings per outfit slot, referencing wardrobe items or catalog products.';
