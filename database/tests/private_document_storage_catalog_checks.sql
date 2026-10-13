-- Catalog checks for the private original-document storage migration.
-- Run only against disposable local Supabase or an approved non-production DB.
DO $checks$
DECLARE
  bucket_is_private boolean;
  storage_rls boolean;
  missing_policies text[];
  storage_path_exists boolean;
BEGIN
  SELECT EXISTS (
    SELECT 1 FROM storage.buckets
    WHERE id = 'documents-private' AND name = 'documents-private' AND public = false
  ) INTO bucket_is_private;

  IF NOT bucket_is_private THEN
    RAISE EXCEPTION 'documents-private bucket is missing or public';
  END IF;

  SELECT c.relrowsecurity
  INTO storage_rls
  FROM pg_class c
  JOIN pg_namespace n ON n.oid = c.relnamespace
  WHERE n.nspname = 'storage' AND c.relname = 'objects';

  IF storage_rls IS DISTINCT FROM true THEN
    RAISE EXCEPTION 'RLS must be enabled on storage.objects';
  END IF;

  SELECT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'documents'
      AND column_name = 'storage_path'
  ) INTO storage_path_exists;

  IF NOT storage_path_exists THEN
    RAISE EXCEPTION 'public.documents.storage_path is missing';
  END IF;

  SELECT array_agg(required.policy_name)
  INTO missing_policies
  FROM (VALUES
    ('documents_private_select_authorized'),
    ('documents_private_insert_authorized'),
    ('documents_private_delete_authorized')
  ) AS required(policy_name)
  WHERE NOT EXISTS (
    SELECT 1 FROM pg_policies p
    WHERE p.schemaname = 'storage'
      AND p.tablename = 'objects'
      AND p.policyname = required.policy_name
      AND 'authenticated' = ANY(p.roles)
  );

  IF cardinality(missing_policies) > 0 THEN
    RAISE EXCEPTION 'Missing storage authorization policies: %',
      array_to_string(missing_policies, ', ');
  END IF;

  IF EXISTS (
    SELECT 1 FROM storage.buckets
    WHERE id = 'documents-private' AND public = true
  ) THEN
    RAISE EXCEPTION 'Private document bucket must never be public';
  END IF;
END
$checks$;
