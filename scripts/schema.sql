-- Run this in the Supabase SQL editor

create table if not exists public.products (
  id uuid primary key default gen_random_uuid(),
  name text not null,
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
alter table public.products enable row level security;
create policy if not exists "Public can read products"
  on public.products for select
  to anon, authenticated
  using (true);
-- Allow authenticated users to insert products (optional, remove in real prod)
create policy if not exists "Auth can insert products"
  on public.products for insert
  to authenticated
  with check (true);

-- Storage: public bucket for product images
-- Run once. If it already exists, this will error; ignore or wrap with DO block if needed.
-- select storage.create_bucket('products', public := true);
-- Policies: allow anon read, authenticated upload/update own objects
-- Note: For stricter control, set public := false and add signed URL flow.
-- Policy names must be unique; use if not exists semantics on dashboard if needed.


create table if not exists public.carts (
  user_id uuid primary key references auth.users(id) on delete cascade,
  created_at timestamptz not null default now()
);
alter table public.carts enable row level security;
create policy if not exists "Users manage own cart"
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
create policy if not exists "Users CRUD own cart items"
  on public.cart_items for all
  to authenticated
  using (auth.uid() = cart_user_id)
  with check (auth.uid() = cart_user_id);
