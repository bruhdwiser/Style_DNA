-- Adds a description column to products for admin form support.
-- The base schema now includes it; this remains safe for older installations.
alter table public.products
  add column if not exists description text;

comment on column public.products.description is 'Short marketing description for product detail and listings.';
