-- Safe ALTERs to extend existing products table
alter table if exists public.products
  add column if not exists category text,
  add column if not exists original_price_cents integer,
  add column if not exists is_new boolean not null default false,
  add column if not exists is_sale boolean not null default false,
  add column if not exists colors text[],
  add column if not exists sizes text[];

-- Create a public bucket for product images (run once)
do $$
begin
  perform storage.create_bucket('products', public := true);
exception when others then
  -- ignore if exists
  null;
end $$;

-- Storage RLS policies for 'products' bucket
-- Public can read
create policy if not exists "Public read products images"
  on storage.objects for select
  using (bucket_id = 'products');

-- Authenticated users can upload
create policy if not exists "Auth upload products images"
  on storage.objects for insert to authenticated
  with check (bucket_id = 'products');

-- Authenticated users can update/delete their own uploads
create policy if not exists "Auth update own products images"
  on storage.objects for update to authenticated
  using (bucket_id = 'products' and owner = auth.uid())
  with check (bucket_id = 'products' and owner = auth.uid());

create policy if not exists "Auth delete own products images"
  on storage.objects for delete to authenticated
  using (bucket_id = 'products' and owner = auth.uid());
