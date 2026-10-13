-- Disposable local-Supabase fixtures for real Storage API authorization tests.
-- Run only after repository migrations and signed_jwt_api_fixtures.sql.
-- All object paths and identities are synthetic. Never run against production.

UPDATE public.documents
SET storage_path = 'b2000000-0000-4000-8000-000000000001/road_asset/e2000000-0000-4000-8000-000000000001/manager-upload.pdf'
WHERE id = 'e2000000-0000-4000-8000-000000000001';

UPDATE public.documents
SET storage_path = 'b2000000-0000-4000-8000-000000000001/finance/e2000000-0000-4000-8000-000000000002/admin-upload.pdf'
WHERE id = 'e2000000-0000-4000-8000-000000000002';

UPDATE public.documents
SET storage_path = 'b2000000-0000-4000-8000-000000000002/road_asset/e2000000-0000-4000-8000-000000000003/other-org.pdf'
WHERE id = 'e2000000-0000-4000-8000-000000000003';

INSERT INTO public.documents (
  id, organization_id, title, document_type, status, uploaded_by, department_code, storage_path
) VALUES
  ('e2000000-0000-4000-8000-000000000004',
   'b2000000-0000-4000-8000-000000000001',
   'JWT Read-only Upload Denial Fixture', 'maintenance_plan', 'processed',
   'a2000000-0000-4000-8000-000000000002', 'road_asset',
   'b2000000-0000-4000-8000-000000000001/road_asset/e2000000-0000-4000-8000-000000000004/readonly-denied.txt'),
  ('e2000000-0000-4000-8000-000000000005',
   'b2000000-0000-4000-8000-000000000001',
   'JWT Cross-department Upload Denial Fixture', 'maintenance_plan', 'processed',
   'a2000000-0000-4000-8000-000000000002', 'road_asset',
   'b2000000-0000-4000-8000-000000000001/road_asset/e2000000-0000-4000-8000-000000000005/finance-denied.txt'),
  ('e2000000-0000-4000-8000-000000000006',
   'b2000000-0000-4000-8000-000000000001',
   'JWT Org-admin Upload Fixture', 'financial_report', 'processed',
   'a2000000-0000-4000-8000-000000000001', 'finance',
   'b2000000-0000-4000-8000-000000000001/finance/e2000000-0000-4000-8000-000000000006/admin-authorized.txt')
ON CONFLICT (id) DO UPDATE
SET storage_path = EXCLUDED.storage_path,
    department_code = EXCLUDED.department_code;
