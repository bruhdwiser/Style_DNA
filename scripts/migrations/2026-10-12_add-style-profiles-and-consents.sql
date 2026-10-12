-- ==============================================================================
-- Forward-Only Migration: Style Profiles and User Consents
-- Date: 2026-10-12
--
-- Description:
-- Creates two new tables for the FlashFit styling personalization flow:
--
--   1. style_profiles - stores user-selected styling preferences
--      (favorite styles, colors, budget range, preferred occasions,
--       self-selected body type).  No raw measurements are stored.
--
--   2. user_consents - tracks explicit, revocable consent grants
--      (e.g. consent to store derived body-fit guidance).
--
-- Safety Guarantees:
-- - Forward-only and additive (CREATE TABLE IF NOT EXISTS).
-- - Does NOT touch existing tables (products, carts, cart_items).
-- - RLS is enabled; each row is scoped to auth.uid().
-- - No destructive operations.
-- ==============================================================================


-- ============================================================
-- 1. style_profiles
-- ============================================================
create table if not exists public.style_profiles (
  user_id        uuid primary key references auth.users(id) on delete cascade,
  -- Styling preferences
  favorite_styles text[]   default '{}',     -- e.g. {'minimal','classic','traditional'}
  favorite_colors text[]   default '{}',     -- e.g. {'navy','blush','burgundy'}
  budget_min      integer  default null,      -- INR * 100 (price_cents convention)
  budget_max      integer  default null,      -- INR * 100 (price_cents convention)
  occasions       text[]   default '{}',     -- e.g. {'casual','work','festive'}
  -- Self-selected body type (optional, never computed from measurements)
  body_type       text     default null,      -- e.g. 'Hourglass','Pear','Rectangle','Inverted Triangle','Apple'
  -- Derived body-fit guidance (stored ONLY with explicit consent; user can edit/delete)
  body_guidance   jsonb    default null,      -- structured guidance from engine, never raw measurements
  -- Onboarding state
  onboarding_complete boolean default false,
  -- Timestamps
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);

alter table public.style_profiles enable row level security;

-- Users can read/insert/update/delete only their own profile
create policy if not exists "Users manage own style profile"
  on public.style_profiles for all
  to authenticated
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

comment on table  public.style_profiles is 'Per-user styling preferences for outfit generation. No raw body measurements stored.';
comment on column public.style_profiles.body_type is 'Self-selected body shape label; optional and user-editable.';
comment on column public.style_profiles.body_guidance is 'Derived fit guidance (not raw measurements). Stored only with explicit revocable consent.';
comment on column public.style_profiles.budget_min is 'Minimum budget in price_cents (INR * 100). Null = no lower bound.';
comment on column public.style_profiles.budget_max is 'Maximum budget in price_cents (INR * 100). Null = no upper bound.';


-- ============================================================
-- 2. user_consents
-- ============================================================
create table if not exists public.user_consents (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null references auth.users(id) on delete cascade,
  -- Consent specifics
  consent_type text not null,             -- e.g. 'body_guidance_storage'
  granted      boolean not null default false,
  granted_at   timestamptz,
  revoked_at   timestamptz,
  -- Unique per user per consent type
  unique (user_id, consent_type)
);

alter table public.user_consents enable row level security;

-- Users can read/insert/update/delete only their own consent records
create policy if not exists "Users manage own consents"
  on public.user_consents for all
  to authenticated
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

comment on table  public.user_consents is 'Tracks explicit, revocable consent grants per user.';
comment on column public.user_consents.consent_type is 'Type of consent: body_guidance_storage, etc.';
comment on column public.user_consents.granted is 'Current consent state. False = revoked.';


-- ============================================================
-- 3. Indexes for common queries
-- ============================================================
create index if not exists idx_user_consents_user_type
  on public.user_consents (user_id, consent_type);

create index if not exists idx_style_profiles_body_type
  on public.style_profiles (body_type)
  where body_type is not null;
