-- Extended seed: run after schema.sql in Supabase SQL editor
insert into public.products (name, price_cents, original_price_cents, image_url, category, is_new, is_sale, colors, sizes)
values
  ('Minimalist Blazer', 18900, 24900, '/placeholder.svg?height=400&width=300&text=Minimalist+Blazer', 'Formal', true, true, ARRAY['Black','Navy','Beige'], ARRAY['XS','S','M','L','XL']),
  ('Streetwear Hoodie', 8900, null, '/placeholder.svg?height=400&width=300&text=Streetwear+Hoodie', 'Casual', false, false, ARRAY['Black','White','Gray'], ARRAY['S','M','L','XL']),
  ('Elegant Midi Dress', 15900, null, '/placeholder.svg?height=400&width=300&text=Elegant+Midi+Dress', 'Formal', true, false, ARRAY['Black','Navy','Burgundy'], ARRAY['XS','S','M','L']),
  ('Casual Denim Jacket', 11900, 14900, '/placeholder.svg?height=400&width=300&text=Casual+Denim+Jacket', 'Casual', false, true, ARRAY['Blue','Black','White'], ARRAY['S','M','L','XL']),
  ('Professional Trousers', 12900, null, '/placeholder.svg?height=400&width=300&text=Professional+Trousers', 'Formal', false, false, ARRAY['Black','Navy','Gray'], ARRAY['XS','S','M','L','XL']),
  ('Trendy Crop Top', 4900, null, '/placeholder.svg?height=400&width=300&text=Trendy+Crop+Top', 'Casual', true, false, ARRAY['White','Black','Pink'], ARRAY['XS','S','M','L']),
  ('Classic White Shirt', 6900, 8900, '/placeholder.svg?height=400&width=300&text=Classic+White+Shirt', 'Formal', false, true, ARRAY['White'], ARRAY['XS','S','M','L','XL']),
  ('Athleisure Joggers', 7900, null, '/placeholder.svg?height=400&width=300&text=Athleisure+Joggers', 'Streetwear', true, false, ARRAY['Gray','Black'], ARRAY['S','M','L','XL']),
  ('Leather Chelsea Boots', 12900, 15900, '/placeholder.svg?height=400&width=300&text=Chelsea+Boots', 'Streetwear', false, true, ARRAY['Black','Brown'], ARRAY['40','41','42','43','44']),
  ('Summer Linen Shirt', 9900, null, '/placeholder.svg?height=400&width=300&text=Linen+Shirt', 'Casual', true, false, ARRAY['Beige','White','Sky Blue'], ARRAY['XS','S','M','L','XL']);
