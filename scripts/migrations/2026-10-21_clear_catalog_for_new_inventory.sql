-- Reset the public rack before loading a new catalog.
-- Run this migration once through the project's Supabase migration workflow.
-- Cart items reference products with a restrictive foreign key, so clear them first.
delete from public.cart_items;
delete from public.products;
