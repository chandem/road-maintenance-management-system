# Database migrations and production rollout

## Important: repository numbers are not the production migration ledger

The SQL files in this directory use repository-oriented names (for example,
`011_department_road_rls.sql`). The live Supabase project records timestamped
versions and currently has 13 entries through
`20261009115736` (`department_access_helper_015`). Those version numbers and
names do **not** prove that a repository file with the same suffix has already
run, or that a numbered repository file is safe to apply next.

**Never deploy these proposals by guessing from the filename or by replaying
all SQL files.** Before a deployment, reconcile each proposal with the actual
production migration history and catalog, then create unique timestamped,
forward-only migration versions in the deployment system. Do not edit or
replay an already-applied production migration.

## Proposed dependency order (not approved for production)

The following order describes dependencies in this feature branch only:

1. `011_department_road_rls.sql` — moves the existing department-role helper
   into `private`, installs a SECURITY INVOKER public wrapper, and adds road
   RLS policies.
2. `012_department_module_rls.sql` — adds department restrictions to module
   tables; depends on the helper/wrapper and existing organization RLS.
3. `013_department_aware_document_access.sql` — adds
   `documents.department_code` and replaces the interim admin-only document
   policies from 012; depends on 011–012.
4. `014_ai_conversation_department_rls.sql` — creates missing conversation
   tables and their policies.
5. `015_road_section_organization_integrity.sql` — preflights/backfills
   section organization IDs and installs integrity triggers.
6. `016_revoke_excess_authenticated_table_privileges.sql` — assumes the
   conversation tables from 014 exist.
7. `017_harden_function_execution_privileges.sql` — assumes the helpers and
   onboarding RPC exist and the helper conversion in 011 has been validated.
8. `018_profile_and_role_privilege_hardening.sql` — restricts direct profile
   writes; depends on verifying the trusted onboarding RPC still works.

This is a proposed test order, **not a statement that all dependencies or
runtime behavior have passed**. Some of these changes interact with existing
policies, backend service-role paths, and frontend signup/profile flows.

## Required release gates

- Use an isolated, non-production Supabase project. No paid development branch
  should be created without explicit approval.
- Reconcile the source migration files with the timestamped production ledger
  and inspect actual function bodies, table grants, policies, and schema.
- Run `database/tests/migration_release_preflight.sql` against the target
  staging database. Resolve every BLOCKER before continuing. It is read-only;
  it reports schema/catalog observations and does not modify data.
- Run `database/tests/road_section_organization_preflight.sql` before 015.
- Apply the proposal sequence only in staging; run
  `database/tests/authorization_catalog_checks.sql` after the schema changes.
- Run the full real-JWT/Data API matrix in
  `database/tests/department_rls_test_plan.md`; service-role requests do not
  count as RLS tests.
- Specifically prove the SECURITY DEFINER onboarding RPC can still create an
  organization, create its admin membership, and set
  `user_profiles.organization_id` after migration 018. Verify duplicate
  onboarding fails transactionally.
- Confirm backend service-role flows, document upload/download/reindex,
  semantic search, and AI message persistence still work.
- Review Supabase Security Advisor findings and record actual staging results.
- Only then prepare a separate, reviewed production rollout with backup and
  rollback/recovery steps. Do not merge or apply production migrations merely
  because source changes or frontend CI pass.

## Findings from the latest read-only production reconciliation

The production catalog was queried read-only. Current observations:

- Live migration history contains 13 entries through
  `20261009115736`; proposals 011–018 are not recorded under those repository
  filenames.
- `public.documents.department_code` is absent, so 013 is required before
  department-aware document policies can be installed.
- `public.ai_conversations`, `public.ai_messages`, and
  `public.ai_message_sources` are absent. Migration 014 must precede 016.
- `public.road_sections.organization_id` exists but is nullable. The previous
  production count showed zero road sections, so the current integrity
  preflight is vacuous; test non-empty parent/section cases in staging.
- Existing profile policies allow users to create/update their own profile by
  row identity. Migration 018's column grants should limit which fields can be
  written, but signup/profile bootstrap must be tested through the real Data API.
- The production onboarding function is owned by `postgres`, is
  `SECURITY DEFINER`, and currently uses `search_path=public, pg_catalog`.
  The proposed 017 change to an empty search path must be checked against the
  exact function body and tested; do not replace its production definition
  with the repository version without explicit reconciliation.
- The current production `public.has_department_role` is
  `SECURITY DEFINER` and has an empty search path. The 011 schema move and
  invoker wrapper must be tested for PostgREST resolution and all policy callers.
- The current production `user_profiles` INSERT policy checks
  `id = auth.uid()`; migration 018 grants INSERT only on `id, full_name`.
  That is structurally compatible with the policy but still needs a signup test.
- Existing organization/member/department RLS policies are permissive. The new
  policies are restrictive and therefore must be tested in combination with
  existing policies, not in isolation.
- Supabase Storage buckets were empty in the last audit and no object policies
  were found. If document binaries will use Storage, add and test object
  authorization; if downloads are server-mediated, verify every endpoint checks
  the parent document before using a service-role client.
- Production has no active department-role assignments. Real role tests must
  use fake users and assignments in staging; do not seed test assignments into
  production for this audit.

## Current status

The new read-only release preflight is committed at
`database/tests/migration_release_preflight.sql`. It checks required relations,
functions, columns, road-section integrity, and lists key function/policy
catalog state. It has **not** been run against a separate staging project because
no staging database is available in the current workflow.

The feature branch's proposed migrations 011–018 have not been applied to
production. No production DDL/DML was executed during this review. The Vercel
status currently reports build-rate-limit failures; these do not establish
whether the SQL migrations are correct.

## Step 34 — backend/frontend compatibility audit

Read-only source review of the feature branch found:

- The frontend currently reads `user_profiles.organization_id` and calls
  `create_organization_for_current_user`; it does not directly insert or
  update profile rows in the reviewed `App.tsx`. The UI's onboarding path must
  still be tested against the **live** RPC signature/body, because production
  uses an `admin` membership role while the repository proposal has differed.
- Document upload is currently server-mediated: the API extracts text and
  stores document metadata plus `extracted_text` in `public.documents`, then
  writes chunks through the caller-JWT client. The reviewed endpoint does not
  upload a binary to Supabase Storage, and no document-binary download endpoint
  was found in the reviewed route file. Do not assume Storage policies solve
  access to this current flow; RLS on documents/chunks and authorization before
  returning extracted text/snippets are the relevant gates.
- Document list/get/search/question/reindex endpoints use the authenticated
  caller's JWT-scoped Supabase client. Department checks in the API complement
  RLS but do not replace it. Keyword and semantic retrieval must continue to
  filter document metadata under the same caller JWT before snippets reach an
  LLM.
- Conversation list/create/read and user-message insert use the caller's
  JWT-scoped client. The backend service-role client is used to persist assistant
  messages and best-effort update the conversation timestamp. This is an
  intentional privileged path that needs tests proving the caller was authorized
  for the parent conversation before any service-role write and that the service
  key is server-only.
- The current frontend provides sign-in and organization creation, but no
  self-service sign-up form was found in the reviewed `App.tsx`. Migration 018
  should not be assumed to have passed signup/profile compatibility merely
  because this frontend has no profile INSERT call; test the actual account
  provisioning flow used for the deployed environment.
- The code audit does not establish runtime authorization correctness. The
  migration preflight and catalog checks still need to run on isolated staging,
  followed by real user JWT tests for each role.

These are source-review findings only. No SQL was applied and no production
data was changed during Step 34.
