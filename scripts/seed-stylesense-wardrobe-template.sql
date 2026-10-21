-- ============================================================================
-- StyleSense wardrobe image import template (13 private garment photos)
-- Optional manual import; not part of the base setup sequence.
--
-- IMPORTANT: Do not run until:
--   1. The wardrobe_items migration has been applied.
--   2. You replace the UUID below with your real auth.users.id.
--   3. Each source image has been uploaded to the private `wardrobe` bucket at
--      the exact object path listed below (under that same user's folder).
--
-- SQL cannot upload local image files. The images remain private wardrobe
-- entries; they are intentionally not inserted into public.products.
-- `image_url` is set to the Storage object key because the API signs
-- `storage_path` when displaying user-owned wardrobe images.
-- ============================================================================

with seed(user_id, source_image, storage_path, category, slot, sub_category,
          primary_color, color_tags, fit, formality, occasions, seasons,
          style_tags, pattern) as (
  values
    ('REPLACE_WITH_YOUR_AUTH_USERS_UUID'::uuid,
     'stylesense_AI/Outfits/Formal_compressed_page-0001.jpg',
     'REPLACE_WITH_YOUR_AUTH_USERS_UUID/wardrobe-seed/formal-shirt.jpg',
     'top', 'top', 'shirt', 'navy', ARRAY['navy', 'white'], 'regular', 2,
     ARRAY['work', 'formal'], ARRAY['all_season'], ARRAY['classic', 'minimal'], 'solid'),
    ('REPLACE_WITH_YOUR_AUTH_USERS_UUID'::uuid,
     'stylesense_AI/Outfits/Winter_20/Winter_20-compressed_page-0001.jpg',
     'REPLACE_WITH_YOUR_AUTH_USERS_UUID/wardrobe-seed/winter-top-01.jpg',
     'top', 'top', 'sweatshirt', 'blue', ARRAY['blue'], 'regular', 0,
     ARRAY['casual', 'college', 'lounge'], ARRAY['winter'], ARRAY['casual'], 'solid'),
    ('REPLACE_WITH_YOUR_AUTH_USERS_UUID'::uuid,
     'stylesense_AI/Outfits/Winter_20/Winter_20-compressed_page-0002.jpg',
     'REPLACE_WITH_YOUR_AUTH_USERS_UUID/wardrobe-seed/winter-top-02.jpg',
     'top', 'top', 'sweatshirt', 'gray', ARRAY['gray'], 'regular', 0,
     ARRAY['casual', 'college', 'lounge'], ARRAY['winter'], ARRAY['casual'], 'solid'),
    ('REPLACE_WITH_YOUR_AUTH_USERS_UUID'::uuid,
     'stylesense_AI/Outfits/Winter_20/Winter_20-compressed_page-0003.jpg',
     'REPLACE_WITH_YOUR_AUTH_USERS_UUID/wardrobe-seed/winter-top-03.jpg',
     'top', 'top', 'sweatshirt', 'black', ARRAY['black'], 'regular', 0,
     ARRAY['casual', 'college', 'lounge'], ARRAY['winter'], ARRAY['casual'], 'solid'),
    ('REPLACE_WITH_YOUR_AUTH_USERS_UUID'::uuid,
     'stylesense_AI/Outfits/Casual_20/Casual_20jeans_20_compressed_page-0001.jpg',
     'REPLACE_WITH_YOUR_AUTH_USERS_UUID/wardrobe-seed/jeans-01.jpg',
     'bottom', 'bottom', 'jeans', 'blue', ARRAY['blue'], 'regular', 0,
     ARRAY['casual', 'college'], ARRAY['all_season'], ARRAY['casual', 'classic'], 'solid'),
    ('REPLACE_WITH_YOUR_AUTH_USERS_UUID'::uuid,
     'stylesense_AI/Outfits/Casual_20/Casual_20jeans_20_compressed_page-0002.jpg',
     'REPLACE_WITH_YOUR_AUTH_USERS_UUID/wardrobe-seed/jeans-02.jpg',
     'bottom', 'bottom', 'jeans', 'blue', ARRAY['blue'], 'regular', 0,
     ARRAY['casual', 'college'], ARRAY['all_season'], ARRAY['casual', 'classic'], 'solid'),
    ('REPLACE_WITH_YOUR_AUTH_USERS_UUID'::uuid,
     'stylesense_AI/Outfits/Casual_20/Casual_20jeans_20_compressed_page-0003.jpg',
     'REPLACE_WITH_YOUR_AUTH_USERS_UUID/wardrobe-seed/jeans-03.jpg',
     'bottom', 'bottom', 'jeans', 'blue', ARRAY['blue'], 'regular', 0,
     ARRAY['casual', 'college'], ARRAY['all_season'], ARRAY['casual', 'classic'], 'solid'),
    ('REPLACE_WITH_YOUR_AUTH_USERS_UUID'::uuid,
     'stylesense_AI/Outfits/Ethnic/Ethnic_20-compressed_page-0001.jpg',
     'REPLACE_WITH_YOUR_AUTH_USERS_UUID/wardrobe-seed/ethnic-top-01.jpg',
     'top', 'top', 'kurta', 'pink', ARRAY['pink'], 'regular', 2,
     ARRAY['festive', 'casual'], ARRAY['all_season'], ARRAY['traditional'], 'solid'),
    ('REPLACE_WITH_YOUR_AUTH_USERS_UUID'::uuid,
     'stylesense_AI/Outfits/Ethnic/Ethnic_20-compressed_page-0002.jpg',
     'REPLACE_WITH_YOUR_AUTH_USERS_UUID/wardrobe-seed/ethnic-top-02.jpg',
     'top', 'top', 'kurta', 'blue', ARRAY['blue'], 'regular', 2,
     ARRAY['festive', 'casual'], ARRAY['all_season'], ARRAY['traditional'], 'solid'),
    ('REPLACE_WITH_YOUR_AUTH_USERS_UUID'::uuid,
     'stylesense_AI/Outfits/Ethnic/Ethnic_20-compressed_page-0003.jpg',
     'REPLACE_WITH_YOUR_AUTH_USERS_UUID/wardrobe-seed/ethnic-top-03.jpg',
     'top', 'top', 'kurta', 'green', ARRAY['green'], 'regular', 2,
     ARRAY['festive', 'casual'], ARRAY['all_season'], ARRAY['traditional'], 'solid'),
    ('REPLACE_WITH_YOUR_AUTH_USERS_UUID'::uuid,
     'stylesense_AI/Outfits/Ethnic/Ethnic_20-compressed_page-0004.jpg',
     'REPLACE_WITH_YOUR_AUTH_USERS_UUID/wardrobe-seed/ethnic-top-04.jpg',
     'top', 'top', 'kurta', 'red', ARRAY['red'], 'regular', 2,
     ARRAY['festive', 'casual'], ARRAY['all_season'], ARRAY['traditional'], 'solid'),
    ('REPLACE_WITH_YOUR_AUTH_USERS_UUID'::uuid,
     'stylesense_AI/Outfits/Ethnic/Ethnic_20-compressed_page-0005.jpg',
     'REPLACE_WITH_YOUR_AUTH_USERS_UUID/wardrobe-seed/ethnic-top-05.jpg',
     'top', 'top', 'kurta', 'cream', ARRAY['cream'], 'regular', 2,
     ARRAY['festive', 'casual'], ARRAY['all_season'], ARRAY['traditional'], 'solid'),
    ('REPLACE_WITH_YOUR_AUTH_USERS_UUID'::uuid,
     'stylesense_AI/Outfits/ezyZip/WhatsApp Image 2026-10-11 at 10.00.03 PM.jpeg',
     'REPLACE_WITH_YOUR_AUTH_USERS_UUID/wardrobe-seed/pink-blouse.jpg',
     'top', 'top', 'blouse', 'pink', ARRAY['pink'], 'regular', 1,
     ARRAY['casual', 'work', 'party'], ARRAY['summer', 'all_season'], ARRAY['feminine'], 'solid')
),
resolved as (
  select user_id, source_image, storage_path, category, slot, sub_category,
         primary_color, color_tags, fit, formality, occasions, seasons,
         style_tags, pattern
  from seed
)
insert into public.wardrobe_items (
  user_id, image_url, storage_path, category, slot, sub_category,
  primary_color, color_tags, fit, formality, occasions, seasons,
  style_tags, pattern, needs_review, metadata
)
select user_id, storage_path, storage_path, category, slot, sub_category,
       primary_color, color_tags, fit, formality, occasions, seasons,
       style_tags, pattern, true,
       jsonb_build_object('source_image', source_image, 'imported_from', 'stylesense_AI/Outfits')
from resolved r
where not exists (
  select 1 from public.wardrobe_items w
  where w.user_id = r.user_id and w.storage_path = r.storage_path
);
