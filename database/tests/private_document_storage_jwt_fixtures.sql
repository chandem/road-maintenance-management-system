-- Private-storage authorization fixtures for disposable local Supabase only.
-- Fixed object names make the expected organization/department/document binding explicit.
UPDATE public.documents
SET storage_path = 'b2000000-0000-4000-8000-000000000001/road_asset/e2000000-0000-4000-8000-000000000001/road-original.pdf'
WHERE id = 'e2000000-0000-4000-8000-000000000001';

UPDATE public.documents
SET storage_path = 'b2000000-0000-4000-8000-000000000001/finance/e2000000-0000-4000-8000-000000000002/finance-original.pdf'
WHERE id = 'e2000000-0000-4000-8000-000000000002';

UPDATE public.documents
SET storage_path = 'b2000000-0000-4000-8000-000000000002/road_asset/e2000000-0000-4000-8000-000000000003/other-org-original.pdf'
WHERE id = 'e2000000-0000-4000-8000-000000000003';

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM public.documents WHERE id = 'e2000000-0000-4000-8000-000000000001' AND storage_path IS NOT NULL)
     OR NOT EXISTS (SELECT 1 FROM public.documents WHERE id = 'e2000000-0000-4000-8000-000000000002' AND storage_path IS NOT NULL)
     OR NOT EXISTS (SELECT 1 FROM public.documents WHERE id = 'e2000000-0000-4000-8000-000000000003' AND storage_path IS NOT NULL) THEN
    RAISE EXCEPTION 'Private-storage fixtures failed to bind expected documents to object paths';
  END IF;
END
$$;
