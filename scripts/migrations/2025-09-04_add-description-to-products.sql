-- Adds a description column to products for admin form support
alter table if exists public.products
  add column if not exists description text;

comment on column public.products.description is 'Short marketing description for product detail and listings.';