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

-- Additional disposable officer identity for testing the officer upload path.
INSERT INTO public.organization_members (organization_id, user_id, role, is_active)
VALUES ('b2000000-0000-4000-8000-000000000001', 'a2000000-0000-4000-8000-000000000006', 'member', true)
ON CONFLICT (organization_id, user_id) DO NOTHING;

INSERT INTO public.user_department_roles (organization_id, user_id, department_id, role, is_active)
VALUES ('b2000000-0000-4000-8000-000000000001', 'a2000000-0000-4000-8000-000000000006', 'c2000000-0000-4000-8000-000000000001', 'officer', true)
ON CONFLICT (organization_id, user_id, department_id) DO NOTHING;

INSERT INTO public.documents (
  id, organization_id, title, document_type, status, uploaded_by, department_code, storage_path
) VALUES (
  'e2000000-0000-4000-8000-000000000004',
  'b2000000-0000-4000-8000-000000000001',
  'JWT Road Officer Original',
  'maintenance_plan',
  'processed',
  'a2000000-0000-4000-8000-000000000006',
  'road_asset',
  'b2000000-0000-4000-8000-000000000001/road_asset/e2000000-0000-4000-8000-000000000004/officer-original.pdf'
)
ON CONFLICT (id) DO UPDATE SET storage_path = EXCLUDED.storage_path;
