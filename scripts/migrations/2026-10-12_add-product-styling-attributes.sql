-- ==============================================================================
-- Forward-Only Migration: Add Styling and Taxonomy Attributes to Products
-- Run fourth, before the style-profile, wardrobe, outfit, and seed scripts.
-- Date: 2026-10-12
--
-- Description:
-- Extends public.products table with additive styling attributes required by
-- the FlashFit / StyleSense pure Python styling rules engine:
--   - audience: target audience ('women', 'men', 'unisex', 'all')
--   - slot: outfit skeleton slot ('top', 'bottom', 'dress', 'saree', 'ethnic_set', 'shoes', 'bag', 'outer', 'jewelry', 'dupatta')
--   - subtype: specific garment or accessory subtype (e.g., 'kurta', 'anarkali', 'trousers', 'jhumka')
--   - color_tags: normalized hex or color name tags
--   - formality: integer formality level (0=casual, 1=smart casual, 2=formal, 3=festive/wedding)
--   - style_tags: aesthetic archetype tags (e.g., 'minimal', 'classic', 'traditional', 'streetwear')
--   - occasions: suitable occasions (e.g., 'casual', 'college', 'work', 'party', 'formal', 'festive', 'wedding', 'lounge')
--   - seasons: suitable seasonal tags (e.g., 'summer', 'winter', 'monsoon', 'all_season')
--   - fit: garment silhouette fit (e.g., 'regular', 'slim', 'relaxed', 'oversized')
--   - pattern: fabric pattern (e.g., 'solid', 'floral', 'striped', 'printed')
--   - seed_key: stable unique key for idempotent demo/catalog seeding
--
-- Safety Guarantees:
-- - Non-destructive and forward-only (ADD COLUMN IF NOT EXISTS).
-- - Existing rows and UUIDs are 100% preserved.
-- - Existing price_cents values are NOT altered.
-- - Does NOT drop tables, alter existing column types, or break existing queries.
-- ==============================================================================

alter table if exists public.products
  add column if not exists description text,
  add column if not exists audience text default 'all',
  add column if not exists slot text,
  add column if not exists subtype text,
  add column if not exists color_tags text[] default '{}',
  add column if not exists formality integer default 1 check (formality is null or (formality >= 0 and formality <= 3)),
  add column if not exists style_tags text[] default '{}',
  add column if not exists occasions text[] default '{}',
  add column if not exists seasons text[] default '{}',
  add column if not exists fit text,
  add column if not exists pattern text,
  add column if not exists seed_key text;

-- The seed uses ON CONFLICT (seed_key); this unique index makes those upserts
-- deterministic and re-runnable. Existing duplicate keys will be reported
-- instead of silently skipping the uniqueness requirement.
create unique index if not exists uq_products_seed_key
  on public.products (seed_key);

-- Column documentation
comment on column public.products.audience is 'Target styling audience: women, men, unisex, all';
comment on column public.products.slot is 'Outfit skeleton slot: top, bottom, dress, saree, ethnic_set, shoes, bag, outer, jewelry, dupatta';
comment on column public.products.subtype is 'Garment or accessory subtype (e.g., blazer, anarkali, trousers, jhumka)';
comment on column public.products.color_tags is 'Normalized color names or hex codes for palette matching';
comment on column public.products.formality is 'Formality level: 0=casual, 1=smart casual, 2=formal, 3=festive/wedding';
comment on column public.products.style_tags is 'Style archetype tags (minimal, classic, traditional, streetwear, etc.)';
comment on column public.products.occasions is 'List of occasions the garment is appropriate for';
comment on column public.products.seasons is 'List of seasons the garment is suitable for';
comment on column public.products.fit is 'Garment silhouette fit (regular, slim, relaxed, oversized)';
comment on column public.products.pattern is 'Fabric pattern (solid, floral, striped, printed)';
comment on column public.products.seed_key is 'Deterministic seed identifier for idempotent upsert operations';

-- Indexing for fast catalog styling queries
create index if not exists idx_products_styling on public.products (slot, audience);
create index if not exists idx_products_formality on public.products (formality);

-- ==============================================================================
-- Idempotent backfill: populate styling attributes for existing seed items.
-- Append each row UUID to the key so duplicate demo products with the same
-- name remain valid under the unique seed_key index.
-- ==============================================================================
update public.products
set audience = 'women',
    slot = 'outer',
    subtype = 'blazer',
    formality = 2,
    style_tags = ARRAY['minimal', 'formal', 'classic'],
    occasions = ARRAY['work', 'formal'],
    seasons = ARRAY['all_season'],
    fit = 'regular',
    pattern = 'solid',
    seed_key = 'existing_minimalist_blazer_' || id::text
where name = 'Minimalist Blazer' and slot is null;

update public.products
set audience = 'unisex',
    slot = 'top',
    subtype = 'hoodie',
    formality = 0,
    style_tags = ARRAY['streetwear', 'casual'],
    occasions = ARRAY['casual', 'college'],
    seasons = ARRAY['winter', 'all_season'],
    fit = 'oversized',
    pattern = 'solid',
    seed_key = 'existing_streetwear_hoodie_' || id::text
where name = 'Streetwear Hoodie' and slot is null;

update public.products
set audience = 'women',
    slot = 'dress',
    subtype = 'midi_dress',
    formality = 2,
    style_tags = ARRAY['classic', 'elegant', 'minimal'],
    occasions = ARRAY['party', 'formal', 'work'],
    seasons = ARRAY['all_season'],
    fit = 'regular',
    pattern = 'solid',
    seed_key = 'existing_elegant_midi_dress_' || id::text
where name = 'Elegant Midi Dress' and slot is null;

update public.products
set audience = 'unisex',
    slot = 'outer',
    subtype = 'denim_jacket',
    formality = 0,
    style_tags = ARRAY['casual', 'streetwear'],
    occasions = ARRAY['casual', 'college'],
    seasons = ARRAY['all_season', 'winter'],
    fit = 'relaxed',
    pattern = 'solid',
    seed_key = 'existing_casual_denim_jacket_' || id::text
where name = 'Casual Denim Jacket' and slot is null;

update public.products
set audience = 'women',
    slot = 'bottom',
    subtype = 'trousers',
    formality = 2,
    style_tags = ARRAY['minimal', 'formal', 'classic'],
    occasions = ARRAY['work', 'formal'],
    seasons = ARRAY['all_season'],
    fit = 'regular',
    pattern = 'solid',
    seed_key = 'existing_professional_trousers_' || id::text
where name = 'Professional Trousers' and slot is null;

update public.products
set audience = 'women',
    slot = 'top',
    subtype = 'crop_top',
    formality = 0,
    style_tags = ARRAY['casual', 'trend'],
    occasions = ARRAY['casual', 'college', 'party'],
    seasons = ARRAY['summer'],
    fit = 'slim',
    pattern = 'solid',
    seed_key = 'existing_trendy_crop_top_' || id::text
where name = 'Trendy Crop Top' and slot is null;

update public.products
set audience = 'unisex',
    slot = 'top',
    subtype = 'shirt',
    formality = 2,
    style_tags = ARRAY['minimal', 'classic', 'formal'],
    occasions = ARRAY['work', 'formal', 'college'],
    seasons = ARRAY['all_season'],
    fit = 'regular',
    pattern = 'solid',
    seed_key = 'existing_classic_white_shirt_' || id::text
where name = 'Classic White Shirt' and slot is null;

update public.products
set audience = 'unisex',
    slot = 'bottom',
    subtype = 'joggers',
    formality = 0,
    style_tags = ARRAY['streetwear', 'casual'],
    occasions = ARRAY['casual', 'lounge'],
    seasons = ARRAY['all_season'],
    fit = 'relaxed',
    pattern = 'solid',
    seed_key = 'existing_athleisure_joggers_' || id::text
where name = 'Athleisure Joggers' and slot is null;

update public.products
set audience = 'unisex',
    slot = 'shoes',
    subtype = 'chelsea_boots',
    formality = 1,
    style_tags = ARRAY['classic', 'streetwear'],
    occasions = ARRAY['casual', 'work', 'party'],
    seasons = ARRAY['all_season', 'winter'],
    fit = 'regular',
    pattern = 'solid',
    seed_key = 'existing_leather_chelsea_boots_' || id::text
where name = 'Leather Chelsea Boots' and slot is null;

update public.products
set audience = 'unisex',
    slot = 'top',
    subtype = 'linen_shirt',
    formality = 1,
    style_tags = ARRAY['relaxed', 'casual', 'minimal'],
    occasions = ARRAY['casual', 'college', 'summer'],
    seasons = ARRAY['summer'],
    fit = 'relaxed',
    pattern = 'solid',
    seed_key = 'existing_summer_linen_shirt_' || id::text
where name = 'Summer Linen Shirt' and slot is null;
