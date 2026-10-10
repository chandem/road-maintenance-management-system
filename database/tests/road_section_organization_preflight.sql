-- Read-only preflight for migration 015_road_section_organization_integrity.sql.
-- Run against a NON-PRODUCTION database before applying migration 015.
-- This script only SELECTs data; it does not repair or modify anything.
--
-- Expected result: zero rows from the blocker query. If blockers exist, resolve
-- them deliberately in staging before applying the migration.

-- Summary counts: useful for recording before/after staging evidence.
SELECT
  count(*) FILTER (WHERE r.id IS NULL) AS orphaned_sections,
  count(*) FILTER (WHERE r.id IS NOT NULL AND r.organization_id IS NULL)
    AS sections_with_parent_missing_organization,
  count(*) FILTER (
    WHERE r.id IS NOT NULL
      AND r.organization_id IS NOT NULL
      AND s.organization_id IS NOT NULL
      AND s.organization_id <> r.organization_id
  ) AS organization_mismatches,
  count(*) FILTER (
    WHERE r.id IS NOT NULL
      AND r.organization_id IS NOT NULL
      AND s.organization_id IS NULL
  ) AS sections_requiring_backfill,
  count(*) AS total_sections
FROM public.road_sections AS s
LEFT JOIN public.roads AS r ON r.id = s.road_id;

-- Detail every condition that would make migration 015 abort.
SELECT
  s.id AS road_section_id,
  s.road_id,
  s.organization_id AS section_organization_id,
  r.organization_id AS parent_road_organization_id,
  CASE
    WHEN r.id IS NULL THEN 'ORPHANED_SECTION_PARENT'
    WHEN r.organization_id IS NULL THEN 'PARENT_ROAD_ORGANIZATION_IS_NULL'
    WHEN s.organization_id IS NOT NULL
      AND s.organization_id <> r.organization_id
      THEN 'SECTION_PARENT_ORGANIZATION_MISMATCH'
  END AS blocker
FROM public.road_sections AS s
LEFT JOIN public.roads AS r ON r.id = s.road_id
WHERE r.id IS NULL
   OR r.organization_id IS NULL
   OR (
     s.organization_id IS NOT NULL
     AND s.organization_id <> r.organization_id
   )
ORDER BY s.id;

-- List only the NULL section organization IDs that migration 015 intends to
-- backfill from a valid parent road. Review the count and IDs in staging first.
SELECT
  s.id AS road_section_id,
  s.road_id,
  r.organization_id AS organization_id_to_backfill
FROM public.road_sections AS s
JOIN public.roads AS r ON r.id = s.road_id
WHERE s.organization_id IS NULL
  AND r.organization_id IS NOT NULL
ORDER BY s.id;
