# Private Original Document Storage — Design Proposal

Status: proposal only; not deployed and not applied to production.

## Current behavior

The upload endpoint in `backend/app/api/routes/documents.py` extracts text and persists document metadata and extracted text in `public.documents`, then creates chunks/embeddings. It does not persist the uploaded original file in object storage, and there is no original-file download endpoint. The current production project has no Storage bucket configured (verified separately by read-only inspection).

## Goals

- Retain original PDF, DOCX, XLSX/XLSM, TXT, and CSV files for later authorized download.
- Keep objects private and scoped to the same organization and department as their document row.
- Reuse the existing Supabase project and free-tier resources; do not create another project or paid resource.
- Preserve the existing JWT-scoped authorization approach; avoid using the service-role key for user uploads/downloads.
- Keep production unchanged until the migration, API tests, and local JWT/RLS checks pass and a separate rollout is approved.

## Proposed storage model

- One private bucket named `documents-private`; no public bucket and no public object URLs.
- Add nullable `storage_path` to `public.documents`. Existing records remain NULL and continue to have no original file available.
- Store only an object path, never a public URL. Use a generated path such as
  `<organization_uuid>/<department_code>/<document_uuid>/<random_uuid>.<validated_extension>`.
  Do not use the user-provided filename as an object path component.
- Keep the original display filename in document metadata/title; keep `file_size_bytes` and `mime_type` as existing metadata.
- The bucket/object upload must occur with the caller's JWT-scoped Supabase client so Storage RLS applies. Do not fall back to service-role access on authorization errors.
- For downloads, first fetch the document row with the caller's JWT-scoped client and call the existing document-row authorization check. Then request a short-lived signed URL (suggested expiry: 60 seconds) for the exact stored path. Return no URL for records with NULL `storage_path`. Never accept a client-supplied object path as authority.

## Authorization requirements

1. Bucket is private.
2. Object path must match the document row's organization, department, document ID, and `storage_path`; a caller cannot choose a different path to access another file.
3. Organization owners/admins may access objects only within their active organization.
4. Department managers/officers may upload/download files for their assigned department; read-only members may download but not upload.
5. Anonymous users and users in another organization/department must be denied by Storage RLS and the API.
6. Unclassified documents (NULL `department_code`) remain admin-only, consistent with current document access policy.
7. Signed URLs are short-lived bearer links; do not log them or store them in the database.
8. Validate extension, size, content type and extracted text as the current upload route does. Use generated object names and avoid trusting the incoming MIME type alone.

Storage RLS policies must not trust path segments alone. They should verify the matching row in `public.documents` and reuse the established active-membership/department-role rules. The policy SQL must be tested on the disposable local Supabase instance before any production proposal is considered.

## Upload consistency and failure handling

- Create the document row and storage object with explicit cleanup/compensation logic. If object upload fails, do not report success; if later chunking/embedding fails, preserve the stored document and report the existing partial-ingestion status rather than deleting a valid original.
- Avoid leaving orphan objects when the document-row insert fails; remove the uploaded object using the same caller-scoped client where possible. Add a regression test for each failure path.
- The current upload response schema must be reviewed before adding any response fields; do not expose internal object paths to clients.

## Test gates before release

- Unit tests: unauthorized user rejected before file read/storage calls; valid upload stores a generated path; storage upload failure leaves no falsely successful document; document-row insert failure triggers best-effort object cleanup; missing original returns 404/409 without generating a URL; download authorization happens before signing; signed URL expiry is short.
- Local Supabase integration: create a private bucket in the disposable test DB, apply Storage policies, and test with genuine local Auth-issued JWTs for same-department manager/officer/read-only, different department, different organization, admin/owner, and anonymous callers.
- Regression: all existing backend tests, SQL catalog checks, migration integration workflow, onboarding RPC regression, and document RLS checks pass.
- Staging is not currently configured. CI success alone is not proof of production parity. Do not call a production rollout ready until the real-JWT staging matrix exists and passes.

## Rollout boundaries

This proposal does not create a bucket, change production schema, apply a migration, deploy backend code, or change Vercel/Render settings. Any production migration, bucket creation, policy installation, merge, or deployment requires a separate explicit approval after reviewing the exact SQL and release plan.
