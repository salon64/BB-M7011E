-- Item Service Database Functions
-- Run this script in your Supabase SQL Editor to create all required functions

-- ============================================================================
-- Table: Items
-- ============================================================================
CREATE TABLE IF NOT EXISTS public."Items" (
  name text NOT NULL DEFAULT ''::text,
  price bigint NOT NULL,
  barcode_id bigint NULL,
  active boolean NOT NULL DEFAULT true,
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  CONSTRAINT items_pkey PRIMARY KEY (id)
) TABLESPACE pg_default;

-- ============================================================================
-- Function: create_item
-- Creates a new item with the provided details
-- ============================================================================
CREATE OR REPLACE FUNCTION public.create_item(
  name_input text,
  price_input bigint,
  barcode_id_input bigint
)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  INSERT INTO public."Items" (name, price, barcode_id, active)
  VALUES (name_input, price_input, barcode_id_input, TRUE);
END;
$$;

-- ============================================================================
-- Function: fetch_item_info
-- Retrieves item information by item ID
-- ============================================================================
CREATE OR REPLACE FUNCTION public.fetch_item_info(
  item_id_input uuid
)
RETURNS json
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  result json;
BEGIN
  SELECT json_build_object(
    'id', id,
    'name', name,
    'price', price,
    'barcode_id', barcode_id,
    'active', active
  ) INTO result
  FROM public."Items"
  WHERE id = item_id_input;

  IF result IS NULL THEN
    RAISE EXCEPTION 'Item not found';
  END IF;

  RETURN result;
END;
$$;

-- ============================================================================
-- Function: item_status
-- Updates an item's active status
-- ============================================================================
CREATE OR REPLACE FUNCTION public.item_status(
  item_id_input uuid,
  item_status_input boolean
)
RETURNS text
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  current_status BOOLEAN;
BEGIN
  SELECT active INTO current_status
  FROM public."Items"
  WHERE id = item_id_input
  FOR UPDATE;

  IF NOT FOUND THEN
    RAISE EXCEPTION 'Item not found';
  END IF;

  IF current_status = item_status_input THEN
    RAISE EXCEPTION 'Item status is already active=%', current_status;
  END IF;

  UPDATE public."Items"
  SET active = item_status_input
  WHERE id = item_id_input;

  RETURN 'Item with id ' || item_id_input || ' has new status active = ' || item_status_input;
END;
$$;

-- ============================================================================
-- Grant permissions for Supabase anonymous/authenticated roles
-- ============================================================================
GRANT EXECUTE ON FUNCTION public.create_item(text, bigint, bigint) TO anon, authenticated, service_role;
GRANT EXECUTE ON FUNCTION public.fetch_item_info(uuid) TO anon, authenticated, service_role;
GRANT EXECUTE ON FUNCTION public.item_status(uuid, boolean) TO anon, authenticated, service_role;