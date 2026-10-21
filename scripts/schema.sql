-- FlashFit base schema — run first in the Supabase SQL Editor.
-- Safe to re-run. Product writes are intentionally restricted to the backend
-- service role; the backend checks admin authorization before changing catalog data.

begin;

create table if not exists public.products (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  description text,
  price_cents integer not null check (price_cents >= 0),
  image_url text,
  category text,
  original_price_cents integer,
  is_new boolean not null default false,
  is_sale boolean not null default false,
  colors text[],
  sizes text[],
  created_at timestamptz not null default now()
);

-- Keep older installations compatible with the current seed and admin forms.
alter table public.products
  add column if not exists description text,
  add column if not exists category text,
  add column if not exists original_price_cents integer,
  add column if not exists is_new boolean not null default false,
  add column if not exists is_sale boolean not null default false,
  add column if not exists colors text[],
  add column if not exists sizes text[];

alter table public.products enable row level security;

drop policy if exists "Public can read products" on public.products;
create policy "Public can read products"
  on public.products for select
  to anon, authenticated
  using (true);
-- Remove the old unrestricted catalog-write policy, if an earlier schema created it.
drop policy if exists "Auth can insert products" on public.products;

create table if not exists public.carts (
  user_id uuid primary key references auth.users(id) on delete cascade,
  created_at timestamptz not null default now()
);
alter table public.carts enable row level security;

drop policy if exists "Users manage own cart" on public.carts;
create policy "Users manage own cart"
  on public.carts for all
  to authenticated
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

create table if not exists public.cart_items (
  id uuid primary key default gen_random_uuid(),
  cart_user_id uuid not null references public.carts(user_id) on delete cascade,
  product_id uuid not null references public.products(id) on delete restrict,
  quantity int not null default 1 check (quantity > 0),
  created_at timestamptz not null default now(),
  unique (cart_user_id, product_id)
);
alter table public.cart_items enable row level security;

drop policy if exists "Users CRUD own cart items" on public.cart_items;
create policy "Users CRUD own cart items"
  on public.cart_items for all
  to authenticated
  using (auth.uid() = cart_user_id)
  with check (auth.uid() = cart_user_id);

grant usage on schema public to anon, authenticated, service_role;
grant select on public.products to anon, authenticated;
grant all on public.products to service_role;
grant select, insert, update, delete on public.carts, public.cart_items to authenticated;
grant all on public.carts, public.cart_items to service_role;

commit;
