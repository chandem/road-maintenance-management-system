# AI Document Authorization Review

Review date: 2026-10-10  
Branch: feature/department-role-management  
Review type: source review only; no database changes or live JWT tests.

## Routes reviewed

- backend/app/api/dependencies.py
- backend/app/api/routes/documents.py
- backend/app/api/routes/ai.py
- backend/app/services/semantic_search.py
- backend/app/services/document_ingestion.py
- Existing document authorization and isolation tests.

## Findings

1. Document listing, detail, keyword search, upload, and reindex use the caller's JWT-scoped Supabase client. No service-role client was found in these document route paths.
2. Department authorization verifies active organization membership. Non-admin users must provide a department and pass the department-role RPC. Write actions require manager/officer roles; reads also allow read-only. Document reindex checks the document's organization and department before indexing.
3. Semantic retrieval is organization-filtered and its results are matched back to document metadata using the caller-scoped client before snippets are returned. Road-priority evidence is additionally restricted to documents explicitly classified as road_asset.
4. Upload and reindex persist extracted text and chunks through the caller-scoped client. No original-file download route was found in the reviewed document router; reindex uses stored extracted text. Do not show a download feature unless a separate authorized file-storage path exists.
5. Organization admins intentionally have organization-wide document access. Non-admins must specify a department.
6. Production schema remains a deployment blocker: the read-only audit found public.documents lacks department_code, while the reviewed API selects or filters on that field. Do not apply proposed migrations directly to production.

## Required validation

Current tests use fakes/test doubles; they do not prove PostgreSQL RLS or actual JWT behavior. Before deployment, use an isolated non-production database to test road, finance, HR, read-only, inactive-member, no-role, and cross-organization access; test upload/reindex denial; and verify semantic search and RPC grants against the reconciled schema.

## Safety record

- Production modified: no
- Migrations applied: none
- Real-user RLS validation claimed: no
- PR #1 merged: no


## Follow-up: cross-module office-assistant document evidence

A follow-up source review found that the organization-admin-only `/ai/office-assistant` route passed semantic-search snippets directly into its prompt after supplying an organization filter, without independently checking each match's parent document metadata. This was weaker than the road-priority evidence path.

The route now resolves matched document IDs through the caller's JWT-scoped `documents` query and includes snippets only when the parent document is verified to belong to the same organization. If the metadata query fails, document evidence is omitted (fail closed).

Regression tests were added in `backend/tests/test_office_assistant_document_isolation.py` for cross-organization and missing-parent results, and for metadata lookup failure. These tests have been committed but have **not yet been executed** in this environment. They use test doubles and do not replace authenticated-JWT/RLS testing in isolated staging.
