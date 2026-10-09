-- Enforce organization consistency between roads and road sections.
-- Source-controlled proposal only. Validate in non-production before applying.
--
-- RLS evaluates the road_sections.organization_id column. Without this integrity
-- guard, a row could claim organization A while referencing a road in organization B.

DO $preflight$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM public.road_sections s
    LEFT JOIN public.roads r ON r.id = s.road_id
    WHERE r.id IS NULL
       OR r.organization_id IS NULL
       OR (s.organization_id IS NOT NULL AND s.organization_id <> r.organization_id)
  ) THEN
    RAISE EXCEPTION
      'Cannot enforce road-section organization consistency: orphaned road, NULL parent organization, or organization mismatch exists. Resolve data in staging first.';
  END IF;
END
$preflight$;

-- Backfill legacy sections from their authoritative parent road.
UPDATE public.road_sections s
SET organization_id = r.organization_id
FROM public.roads r
WHERE r.id = s.road_id
  AND s.organization_id IS NULL;

ALTER TABLE public.road_sections
  ALTER COLUMN organization_id SET NOT NULL;

CREATE OR REPLACE FUNCTION private.enforce_road_section_organization()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $function$
DECLARE
  parent_organization_id uuid;
BEGIN
  SELECT r.organization_id
    INTO parent_organization_id
  FROM public.roads AS r
  WHERE r.id = NEW.road_id;

  IF NOT FOUND OR parent_organization_id IS NULL THEN
    RAISE EXCEPTION 'Road section must reference a road with an organization'
      USING ERRCODE = '23503';
  END IF;

  IF NEW.organization_id IS NOT NULL
     AND NEW.organization_id <> parent_organization_id THEN
    RAISE EXCEPTION 'Road section organization must match its parent road'
      USING ERRCODE = '23514';
  END IF;

  -- Derive the organization from the parent, never from client input.
  NEW.organization_id := parent_organization_id;
  RETURN NEW;
END;
$function$;

REVOKE ALL ON FUNCTION private.enforce_road_section_organization() FROM PUBLIC;
REVOKE ALL ON FUNCTION private.enforce_road_section_organization() FROM anon;
REVOKE ALL ON FUNCTION private.enforce_road_section_organization() FROM authenticated;
REVOKE ALL ON FUNCTION private.enforce_road_section_organization() FROM service_role;

DROP TRIGGER IF EXISTS enforce_road_section_organization
  ON public.road_sections;

CREATE TRIGGER enforce_road_section_organization
BEFORE INSERT OR UPDATE OF road_id, organization_id
ON public.road_sections
FOR EACH ROW
EXECUTE FUNCTION private.enforce_road_section_organization();

COMMENT ON FUNCTION private.enforce_road_section_organization() IS
  'Derives road_sections.organization_id from the parent road and rejects cross-organization references.';
