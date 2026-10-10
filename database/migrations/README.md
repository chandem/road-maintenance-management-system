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

The following order describes dependencies in the feature branch only:

1. `011_department_road_rls.sql` — moves the existing department-role helper
   into `private`, installs a SECURITY INVOKER public wrapper, and adds road
   RLS policies.
2. `012_department_module_rls.sql` — adds department restrictions to module
   tables; depends on the helper/wrapper and existing organization RLS.
3. `013_department_aware_document_access.sql` — adds
   `documents.department_code` and parent-aware chunk policies; depends on
   011–012.
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

## Current status

The live production migration ledger has been inspected read-only and contains
13 timestamped entries. The feature branch's proposed migrations 011–018 have
not been applied to production. No staging database is available in the current
workflow, and no production DDL was executed during this review.
