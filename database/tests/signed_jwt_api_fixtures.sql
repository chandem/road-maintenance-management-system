-- Persistent fixtures for signed-JWT/PostgREST tests.
-- Runs only in disposable local Supabase CI after a clean database reset.
-- Never run against a shared or production database.

INSERT INTO auth.users (
  id, aud, role, email, encrypted_password, email_confirmed_at,
  raw_app_meta_data, raw_user_meta_data, created_at, updated_at
) VALUES
  ('a2000000-0000-4000-8000-000000000001', 'authenticated', 'authenticated', 'jwt-admin@example.com', extensions.crypt('Local-CI-only-Road-Role-1-92!', extensions.gen_salt('bf')), now(), '{"provider":"email","providers":["email"]}'::jsonb, '{}'::jsonb, now(), now()),
  ('a2000000-0000-4000-8000-000000000002', 'authenticated', 'authenticated', 'jwt-road-manager@example.com', extensions.crypt('Local-CI-only-Road-Role-2-92!', extensions.gen_salt('bf')), now(), '{"provider":"email","providers":["email"]}'::jsonb, '{}'::jsonb, now(), now()),
  ('a2000000-0000-4000-8000-000000000003', 'authenticated', 'authenticated', 'jwt-road-readonly@example.com', extensions.crypt('Local-CI-only-Road-Role-3-92!', extensions.gen_salt('bf')), now(), '{"provider":"email","providers":["email"]}'::jsonb, '{}'::jsonb, now(), now()),
  ('a2000000-0000-4000-8000-000000000004', 'authenticated', 'authenticated', 'jwt-finance@example.com', extensions.crypt('Local-CI-only-Road-Role-4-92!', extensions.gen_salt('bf')), now(), '{"provider":"email","providers":["email"]}'::jsonb, '{}'::jsonb, now(), now()),
  ('a2000000-0000-4000-8000-000000000005', 'authenticated', 'authenticated', 'jwt-other-org@example.com', extensions.crypt('Local-CI-only-Road-Role-5-92!', extensions.gen_salt('bf')), now(), '{"provider":"email","providers":["email"]}'::jsonb, '{}'::jsonb, now(), now())
ON CONFLICT (id) DO UPDATE SET
  email = EXCLUDED.email,
  encrypted_password = EXCLUDED.encrypted_password,
  email_confirmed_at = EXCLUDED.email_confirmed_at,
  raw_app_meta_data = EXCLUDED.raw_app_meta_data,
  updated_at = now();

-- GoTrue password sign-in also expects the corresponding email identity rows.
INSERT INTO auth.identities (
  provider_id, user_id, identity_data, provider, last_sign_in_at, created_at, updated_at
)
SELECT
  id::text,
  id,
  jsonb_build_object('sub', id::text, 'email', email, 'email_verified', true),
  'email',
  now(),
  now(),
  now()
FROM auth.users
WHERE id IN (
  'a2000000-0000-4000-8000-000000000001',
  'a2000000-0000-4000-8000-000000000002',
  'a2000000-0000-4000-8000-000000000003',
  'a2000000-0000-4000-8000-000000000004',
  'a2000000-0000-4000-8000-000000000005'
)
ON CONFLICT (provider_id, provider) DO UPDATE SET
  user_id = EXCLUDED.user_id,
  identity_data = EXCLUDED.identity_data,
  updated_at = now();

-- Fail early if the disposable fixture password hashes do not match their known passwords.
DO $
DECLARE
  fixture RECORD;
BEGIN
  FOR fixture IN
    SELECT id, encrypted_password, email
    FROM auth.users
    WHERE id IN (
      'a2000000-0000-4000-8000-000000000001',
      'a2000000-0000-4000-8000-000000000002',
      'a2000000-0000-4000-8000-000000000003',
      'a2000000-0000-4000-8000-000000000004',
      'a2000000-0000-4000-8000-000000000005'
    )
  LOOP
    IF fixture.encrypted_password IS NULL OR fixture.encrypted_password = '' THEN
      RAISE EXCEPTION 'Missing password hash for disposable Auth fixture %', fixture.email;
    END IF;
  END LOOP;
END $;

INSERT INTO public.organizations (id, name, code) VALUES
  ('b2000000-0000-4000-8000-000000000001', 'Signed JWT Test Organization A', 'JWT-TEST-A'),
  ('b2000000-0000-4000-8000-000000000002', 'Signed JWT Test Organization B', 'JWT-TEST-B')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.organization_members (organization_id, user_id, role, is_active) VALUES
  ('b2000000-0000-4000-8000-000000000001', 'a2000000-0000-4000-8000-000000000001', 'admin', true),
  ('b2000000-0000-4000-8000-000000000001', 'a2000000-0000-4000-8000-000000000002', 'member', true),
  ('b2000000-0000-4000-8000-000000000001', 'a2000000-0000-4000-8000-000000000003', 'member', true),
  ('b2000000-0000-4000-8000-000000000001', 'a2000000-0000-4000-8000-000000000004', 'member', true),
  ('b2000000-0000-4000-8000-000000000002', 'a2000000-0000-4000-8000-000000000005', 'member', true)
ON CONFLICT (organization_id, user_id) DO NOTHING;

INSERT INTO public.departments (id, organization_id, name, code) VALUES
  ('c2000000-0000-4000-8000-000000000001', 'b2000000-0000-4000-8000-000000000001', 'JWT Road Asset', 'road_asset'),
  ('c2000000-0000-4000-8000-000000000002', 'b2000000-0000-4000-8000-000000000001', 'JWT Finance', 'finance')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.user_department_roles (organization_id, user_id, department_id, role, is_active) VALUES
  ('b2000000-0000-4000-8000-000000000001', 'a2000000-0000-4000-8000-000000000002', 'c2000000-0000-4000-8000-000000000001', 'department_manager', true),
  ('b2000000-0000-4000-8000-000000000001', 'a2000000-0000-4000-8000-000000000003', 'c2000000-0000-4000-8000-000000000001', 'read_only', true),
  ('b2000000-0000-4000-8000-000000000001', 'a2000000-0000-4000-8000-000000000004', 'c2000000-0000-4000-8000-000000000002', 'department_manager', true)
ON CONFLICT (organization_id, user_id, department_id) DO NOTHING;

INSERT INTO public.roads (id, organization_id, road_code, name) VALUES
  ('d2000000-0000-4000-8000-000000000001', 'b2000000-0000-4000-8000-000000000001', 'JWT-A-ROAD', 'Signed JWT Road A'),
  ('d2000000-0000-4000-8000-000000000002', 'b2000000-0000-4000-8000-000000000002', 'JWT-B-ROAD', 'Signed JWT Road B')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.documents (
  id, organization_id, title, document_type, status, uploaded_by, department_code
) VALUES
  ('e2000000-0000-4000-8000-000000000001', 'b2000000-0000-4000-8000-000000000001', 'JWT Road Document', 'maintenance_plan', 'processed', 'a2000000-0000-4000-8000-000000000002', 'road_asset'),
  ('e2000000-0000-4000-8000-000000000002', 'b2000000-0000-4000-8000-000000000001', 'JWT Finance Document', 'financial_report', 'processed', 'a2000000-0000-4000-8000-000000000004', 'finance'),
  ('e2000000-0000-4000-8000-000000000003', 'b2000000-0000-4000-8000-000000000002', 'JWT Other Organization Document', 'maintenance_plan', 'processed', 'a2000000-0000-4000-8000-000000000005', 'road_asset')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.document_chunks (
  id, document_id, organization_id, chunk_index, content, embedding_status
) VALUES
  ('f2000000-0000-4000-8000-000000000001', 'e2000000-0000-4000-8000-000000000001', 'b2000000-0000-4000-8000-000000000001', 0, 'Synthetic road maintenance content', 'complete'),
  ('f2000000-0000-4000-8000-000000000002', 'e2000000-0000-4000-8000-000000000002', 'b2000000-0000-4000-8000-000000000001', 0, 'Synthetic finance content', 'complete'),
  ('f2000000-0000-4000-8000-000000000003', 'e2000000-0000-4000-8000-000000000003', 'b2000000-0000-4000-8000-000000000002', 0, 'Synthetic other organization content', 'complete')
ON CONFLICT (id) DO NOTHING;


-- Existing conversations/messages exercise ownership and append-only policy paths.
INSERT INTO public.ai_conversations (id, organization_id, created_by, title, status)
VALUES
  ('72000000-0000-4000-8000-000000000001', 'b2000000-0000-4000-8000-000000000001', 'a2000000-0000-4000-8000-000000000003', 'Read-only owner conversation', 'active'),
  ('72000000-0000-4000-8000-000000000002', 'b2000000-0000-4000-8000-000000000001', 'a2000000-0000-4000-8000-000000000002', 'Archived manager conversation', 'archived')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.ai_messages (id, conversation_id, role, content)
VALUES
  ('82000000-0000-4000-8000-000000000001', '72000000-0000-4000-8000-000000000001', 'user', 'Synthetic private conversation message'),
  ('82000000-0000-4000-8000-000000000002', '72000000-0000-4000-8000-000000000002', 'user', 'Synthetic archived conversation message')
ON CONFLICT (id) DO NOTHING;
