-- ==============================================================================
-- Forward-Only Migration: Add Variant Fields to Cart Items
-- Date: 2026-10-12
--
-- Description:
-- Adds optional selected_color and selected_size columns to public.cart_items.
-- This migration is forward-only, idempotent, and non-destructive:
-- - Existing rows are preserved with NULL values for the new columns.
-- - No tables, policies, or constraints are dropped.
-- ==============================================================================

alter table if exists public.cart_items
  add column if not exists selected_color text,
  add column if not exists selected_size text;

comment on column public.cart_items.selected_color is 'Optional color selection for the cart item';
comment on column public.cart_items.selected_size is 'Optional size selection for the cart item';
