-- Department-aware document ownership and retrieval.
-- Source-controlled proposal only: do NOT apply to production until the staging
-- matrix in database/tests/department_rls_test_plan.md passes with real JWTs.
--
-- Existing records are deliberately left NULL and remain organization-admin-only
-- until an administrator explicitly classifies them. Never infer ownership from
-- filenames or document_type: those values are not authoritative ACLs.

ALTER TABLE public.documents
  ADD COLUMN IF NOT EXISTS department_code text;

ALTER TABLE public.documents
  DROP CONSTRAINT IF EXISTS documents_department_code_check;

ALTER TABLE public.documents
  ADD CONSTRAINT documents_department_code_check
  CHECK (
    department_code IS NULL
    OR department_code IN (
      'road_asset',
      'machinery_maintenance',
      'finance',
      'human_resources',
      'general_assets'
    )
  );

CREATE INDEX IF NOT EXISTS idx_documents_org_department_created
  ON public.documents (organization_id, department_code, created_at DESC);

-- Replace the interim admin-only restrictive policies from migration 012.
-- A NULL department_code (including all pre-existing records) is admin-only.
DROP POLICY IF EXISTS department_scope_access ON public.documents;
DROP POLICY IF EXISTS documents_department_select ON public.documents;
DROP POLICY IF EXISTS documents_department_insert ON public.documents;
DROP POLICY IF EXISTS documents_department_update ON public.documents;
DROP POLICY IF EXISTS documents_department_delete ON public.documents;

CREATE POLICY documents_department_select
  ON public.documents AS RESTRICTIVE FOR SELECT TO authenticated
  USING (
    private.is_org_admin(organization_id)
    OR (
      department_code IS NOT NULL
      AND public.has_department_role(
        organization_id,
        department_code,
        ARRAY['department_manager', 'officer', 'read_only']::text[]
      )
    )
  );

CREATE POLICY documents_department_insert
  ON public.documents AS RESTRICTIVE FOR INSERT TO authenticated
  WITH CHECK (
    private.is_org_admin(organization_id)
    OR (
      department_code IS NOT NULL
      AND public.has_department_role(
        organization_id,
        department_code,
        ARRAY['department_manager', 'officer']::text[]
      )
    )
  );

CREATE POLICY documents_department_update
  ON public.documents AS RESTRICTIVE FOR UPDATE TO authenticated
  USING (
    private.is_org_admin(organization_id)
    OR (
      department_code IS NOT NULL
      AND public.has_department_role(
        organization_id,
        department_code,
        ARRAY['department_manager', 'officer']::text[]
      )
    )
  )
  WITH CHECK (
    private.is_org_admin(organization_id)
    OR (
      department_code IS NOT NULL
      AND public.has_department_role(
        organization_id,
        department_code,
        ARRAY['department_manager', 'officer']::text[]
      )
    )
  );

CREATE POLICY documents_department_delete
  ON public.documents AS RESTRICTIVE FOR DELETE TO authenticated
  USING (
    private.is_org_admin(organization_id)
    OR (
      department_code IS NOT NULL
      AND public.has_department_role(
        organization_id,
        department_code,
        ARRAY['department_manager', 'officer']::text[]
      )
    )
  );

-- Chunk access must always resolve to a real parent document in the same
-- organization, including for administrators. Do not let the admin branch
-- bypass the parent/organization integrity check or permit orphan/cross-org chunks.
-- The department is inherited from the parent; never trust a caller-supplied code.
DROP POLICY IF EXISTS department_scope_access ON public.document_chunks;
DROP POLICY IF EXISTS document_chunks_department_select ON public.document_chunks;
DROP POLICY IF EXISTS document_chunks_department_insert ON public.document_chunks;
DROP POLICY IF EXISTS document_chunks_department_update ON public.document_chunks;
DROP POLICY IF EXISTS document_chunks_department_delete ON public.document_chunks;

CREATE POLICY document_chunks_department_select
  ON public.document_chunks AS RESTRICTIVE FOR SELECT TO authenticated
  USING (
    EXISTS (
      SELECT 1
      FROM public.documents d
      WHERE d.id = document_chunks.document_id
        AND d.organization_id = document_chunks.organization_id
        AND (
          private.is_org_admin(document_chunks.organization_id)
          OR (
            d.department_code IS NOT NULL
            AND public.has_department_role(
              d.organization_id,
              d.department_code,
              ARRAY['department_manager', 'officer', 'read_only']::text[]
            )
          )
        )
    )
  );

CREATE POLICY document_chunks_department_insert
  ON public.document_chunks AS RESTRICTIVE FOR INSERT TO authenticated
  WITH CHECK (
    EXISTS (
      SELECT 1
      FROM public.documents d
      WHERE d.id = document_chunks.document_id
        AND d.organization_id = document_chunks.organization_id
        AND (
          private.is_org_admin(document_chunks.organization_id)
          OR (
            d.department_code IS NOT NULL
            AND public.has_department_role(
              d.organization_id,
              d.department_code,
              ARRAY['department_manager', 'officer']::text[]
            )
          )
        )
    )
  );

CREATE POLICY document_chunks_department_update
  ON public.document_chunks AS RESTRICTIVE FOR UPDATE TO authenticated
  USING (
    EXISTS (
      SELECT 1
      FROM public.documents d
      WHERE d.id = document_chunks.document_id
        AND d.organization_id = document_chunks.organization_id
        AND (
          private.is_org_admin(document_chunks.organization_id)
          OR (
            d.department_code IS NOT NULL
            AND public.has_department_role(
              d.organization_id,
              d.department_code,
              ARRAY['department_manager', 'officer']::text[]
            )
          )
        )
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1
      FROM public.documents d
      WHERE d.id = document_chunks.document_id
        AND d.organization_id = document_chunks.organization_id
        AND (
          private.is_org_admin(document_chunks.organization_id)
          OR (
            d.department_code IS NOT NULL
            AND public.has_department_role(
              d.organization_id,
              d.department_code,
              ARRAY['department_manager', 'officer']::text[]
            )
          )
        )
    )
  );

CREATE POLICY document_chunks_department_delete
  ON public.document_chunks AS RESTRICTIVE FOR DELETE TO authenticated
  USING (
    EXISTS (
      SELECT 1
      FROM public.documents d
      WHERE d.id = document_chunks.document_id
        AND d.organization_id = document_chunks.organization_id
        AND (
          private.is_org_admin(document_chunks.organization_id)
          OR (
            d.department_code IS NOT NULL
            AND public.has_department_role(
              d.organization_id,
              d.department_code,
              ARRAY['department_manager', 'officer']::text[]
            )
          )
        )
    )
  );

-- match_document_chunks is SECURITY INVOKER in the current schema, so the
-- restrictive RLS policy on document_chunks filters semantic matches before
-- they can reach the API or an LLM prompt. Keep it SECURITY INVOKER.
-- Keyword search must query documents with the caller's JWT too; its RLS policy
-- applies the same department filter before extracted text is returned.
