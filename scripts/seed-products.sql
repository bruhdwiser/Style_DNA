-- Optional minimal demo seed. The main setup uses seed-styling-products.sql.
-- Safe to re-run and does not overwrite products already in the catalog.
with seed(name, price_cents, image_url) as (
  values
    ('Minimalist Blazer', 18900, '/placeholder.svg?height=400&width=300&text=Minimalist+Blazer'),
    ('Streetwear Hoodie', 8900, '/placeholder.svg?height=400&width=300&text=Streetwear+Hoodie'),
    ('Elegant Midi Dress', 15900, '/placeholder.svg?height=400&width=300&text=Elegant+Midi+Dress')
)
insert into public.products (name, price_cents, image_url)
select seed.name, seed.price_cents, seed.image_url
from seed
where not exists (
  select 1 from public.products p where p.name = seed.name
);
