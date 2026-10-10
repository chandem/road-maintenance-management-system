# AI Document Authorization Review

Review date: 2026-10-10  
Branch: feature/department-role-management  
Review type: source review only; no database changes or live JWT tests.

## Routes reviewed

- backend/app/api/dependencies.py
- backend/app/api/routes/documents.py
- backend/app/api/routes/ai.py
- backend/app/api/routes/conversations.py
- backend/app/services/semantic_search.py
- backend/app/services/document_ingestion.py
- Existing document, office-assistant, and conversation authorization tests.

## Findings

1. Document listing, detail, keyword search, upload, and reindex use the caller's JWT-scoped Supabase client. No service-role client was found in these document route paths.
2. Department authorization verifies active organization membership. Non-admin users must provide a department and pass the department-role RPC. Write actions require manager/officer roles; reads also allow read-only. Document reindex checks the document's organization and department before indexing.
3. Semantic retrieval is organization-filtered and its results are matched back to document metadata using the caller-scoped client before snippets are returned. Road-priority evidence is additionally restricted to documents explicitly classified as road_asset.
4. Upload and reindex persist extracted text and chunks through the caller-scoped client. No original-file download route was found in the reviewed document router; reindex uses stored extracted text. Do not show a download feature unless a separate authorized file-storage path exists.
5. Organization admins intentionally have organization-wide document access. Non-admins must specify a department.
6. Production schema remains a deployment blocker: the read-only audit found public.documents lacks department_code, while the reviewed API selects or filters on that field. Do not apply proposed migrations directly to production.

## Conversation and generated-answer authorization review

1. Conversation list/create/read/message routes use the caller's JWT-scoped Supabase client for conversation authorization and user-authored messages.
2. The message-read route verifies that the parent conversation is visible before querying ai_messages; a missing or inaccessible conversation returns 404 without attempting to read its messages.
3. Message posting verifies the parent conversation is visible and has status active before requesting the trusted service client or writing a user message. Archived and missing conversations are rejected.
4. The assistant response is persisted through the server-only service client only after the caller-scoped query verifies access to the parent conversation. If the trusted client is unavailable, the route fails before persisting the user message. Assistant storage failures return a clear 503 recovery message.
5. The proposed migration 014 restricts authenticated message inserts to role='user', while assistant/system messages are intended to be written only by the trusted backend. Authenticated message reads inherit access from the parent conversation. These database policies remain unvalidated against real JWTs because the migration has not been applied in an isolated staging database.
6. No conversation archive/update API route was found in the reviewed conversation router. The migration intentionally grants no authenticated UPDATE privilege for conversations. If an archive/restore feature is added, it must define an explicit role policy and test active-status enforcement against concurrent requests.
7. Added backend/tests/test_conversation_status_security.py to verify archived and missing conversations are rejected before requesting the trusted service client or attempting message persistence. This is a source-level regression test using fakes, not live RLS proof.

## Required validation

Current tests use fakes/test doubles; they do not prove PostgreSQL RLS or actual JWT behavior. Before deployment, use an isolated non-production database to test road, finance, HR, read-only, inactive-member, no-role, and cross-organization access; test upload/reindex denial; and verify semantic search and RPC grants against the reconciled schema. For conversations, test real-JWT direct Data API access, owner and admin boundaries, archived conversations, and rejection of direct assistant/system message inserts.

## Safety record

- Production modified: no
- Migrations applied: none
- Real-user RLS validation claimed: no
- PR #1 merged: no

## Follow-up: cross-module office-assistant document evidence

A follow-up source review found that the organization-admin-only /ai/office-assistant route passed semantic-search snippets directly into its prompt after supplying an organization filter, without independently checking each match's parent document metadata. This was weaker than the road-priority evidence path.

The route now resolves matched document IDs through the caller's JWT-scoped documents query and includes snippets only when the parent document is verified to belong to the same organization. If the metadata query fails, document evidence is omitted (fail closed).

Regression tests were added in backend/tests/test_office_assistant_document_isolation.py for cross-organization and missing-parent results, and for metadata lookup failure. The conversation-status regression tests are also committed. These tests use test doubles and do not replace authenticated-JWT/RLS testing in isolated staging.