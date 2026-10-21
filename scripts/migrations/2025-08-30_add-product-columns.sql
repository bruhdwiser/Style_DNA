-- Legacy additive product migration. The current base schema already includes
-- these columns; this file remains safe for older installations.
alter table if exists public.products
  add column if not exists category text,
  add column if not exists original_price_cents integer,
  add column if not exists is_new boolean not null default false,
  add column if not exists is_sale boolean not null default false,
  add column if not exists colors text[],
  add column if not exists sizes text[];

-- Create the `products` bucket in Supabase Storage (Dashboard -> Storage) and
-- mark it public. A public bucket does not require signed-in upload policies.
-- This legacy migration only grants object reads; product writes go through the
-- backend's admin-checked service-role API.
drop policy if exists "Public read products images" on storage.objects;
create policy "Public read products images"
  on storage.objects for select
  to anon, authenticated
  using (bucket_id = 'products');

drop policy if exists "Auth upload products images" on storage.objects;
drop policy if exists "Auth update own products images" on storage.objects;
drop policy if exists "Auth delete own products images" on storage.objects;
