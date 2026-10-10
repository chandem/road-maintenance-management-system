# Production Migration Readiness Review

**Status: NOT READY for direct production application.** This document records a read-only review of Supabase project `firzbqzbezuecvplsibi` on 2026-10-10. No database writes or migrations were executed.

## Current production migration history

Supabase reports these applied migration names at the latest version:

- `initial_ai_rmms_schema`
- `document_intelligence`
- `document_embeddings`
- `authorization_foundation`
- `secure_semantic_search`
- `add_organization_onboarding_rpc`
- `materials_inventory_009`
- `road_inspections_010`
- `seed_core_departments_011`
- `create_department_role_assignments_012`
- `secure_department_role_assignments_013`
- `department_role_policies_014`
- `department_access_helper_015`

## Findings and blockers

### 1. Migration history and source-control ledger need reconciliation

The live Supabase migration ledger uses timestamp versions (for example, `20261009115651` through `20261009115736`) with descriptive names such as `seed_core_departments_011` and `department_role_policies_014`. The repository also contains proposal files named `011_department_road_rls.sql` and `014_ai_conversation_department_rls.sql`.

This is a **source-control naming/ledger reconciliation issue, not proof of a duplicate live migration version**: the live versions are timestamps, while the repository filenames use descriptive numeric prefixes. Before deployment, map each proposal to a unique timestamped migration version and verify the repository contains the SQL that corresponds to the migrations already applied. Do not rename or replay already-applied production migrations, and do not assume the numbered filenames match the live ledger entries.

### 2. The live security advisor reports exposed SECURITY DEFINER functions

The read-only Supabase security advisor reported:
- `public.has_department_role(uuid,text,text[])` is executable by `anon` and `authenticated` while SECURITY DEFINER.
- `public.create_organization_for_current_user(text,text)` is executable by `authenticated` while SECURITY DEFINER.
- Leaked-password protection is disabled in Auth.

Migration proposals 011 and 017 intend to tighten function execution and name resolution. They still require dependency review and testing before production application. The Auth password setting is a separate dashboard/configuration hardening task, not a SQL migration.

### 3. Road-data policies need authenticated-user validation

Migration 011 moves the role helper into `private`, creates a public SECURITY INVOKER wrapper, and adds restrictive department policies to roads, road sections, and road inspections. Validate function permissions, PostgREST RPC resolution, and actual access for organization admins, department managers, officers, read-only users, and users without road-asset assignments. In production, `road_sections.organization_id` is nullable and there are currently no road-section rows, so the live data cannot establish that these policies behave correctly for populated records.

### 4. AI conversation schema and policies are not yet validated

The live schema review found `ai_conversations`, `ai_messages`, and `ai_message_sources` absent, while backend routes refer to AI conversation storage. Migration 014 proposes creating these tables and applying ownership/department RLS. Test the backend's actual query patterns, message insertion rules, service-role writes, and source-row behavior before applying it.

### 5. Migration 016 must follow the schema migration and be rechecked

Migration 016 revokes TRUNCATE, REFERENCES, and TRIGGER privileges from broad roles on multiple tables, including AI conversation tables introduced by migration 014. Confirm all target relations exist at the point this migration runs, and verify that no supported application workflow depends on any privilege being removed. Preserve a reviewed rollback/recovery plan.

### 6. Migration 017 depends on 011

Migration 017 changes grants for both public and private helper functions and hardens the organization-creation RPC. It depends on the private helper being present and on the expected function signatures. Apply only after the function migration has been validated and the sequence reconciled.

### 7. Static dependency review found grant checks that need to be explicit

The source-controlled proposals 011, 012, 013, and 014 call private helper functions from authenticated RLS policy expressions. In particular, policies call `private.is_org_admin(uuid)`; migration 014 also calls `private.is_org_member(uuid)`. Migration 011 explicitly grants authenticated access to `private.has_department_role`, but does not itself grant execute on the organization helper functions.

This may work if the earlier authorization foundation migration already grants the necessary execute privileges, but that has not been confirmed from the applied SQL source. Do not add grants blindly: inspect the exact function signatures and intended role grants from the applied authorization migration first. The catalog regression script checks `private.is_org_admin(uuid)` but does not currently assert that authenticated can execute `private.is_org_member(uuid)`; add that assertion before relying on the script as a complete check for migration 014.

### 8. Migration 015 is data-changing, not just a policy change

Migration 015 runs a preflight, backfills NULL `road_sections.organization_id` values from parent roads, changes the column to NOT NULL, and installs a trigger. It intentionally aborts if orphaned sections, missing parent organizations, or organization mismatches exist. Run the read-only preflight and record its counts in a non-production environment first; then validate the backfill and trigger behavior. The live production table currently has zero road-section rows, but that does not replace staging validation or production approval.

### 9. Migration 014 needs route-to-policy integration validation

The backend conversation route reads conversations and messages with the caller's JWT, inserts user messages with that client, and saves assistant replies using the server-only service client. The SQL proposal is aligned with that separation at a high level. Still, verify the complete role/ownership matrix with JWTs, including that a road read-only user can list/read only their own conversations but cannot create or post, and that direct Data API inserts cannot forge assistant/system messages or evidence-source rows. Catalog checks alone cannot prove these row-level outcomes.

The catalog regression script has now been strengthened to explicitly verify that `authenticated` can execute `private.is_org_member(uuid)`, which is used by the migration 014 conversation policies. This is a source change only; the SQL script has not been run against production or an isolated staging database. The grant's presence and actual policy behavior still require a controlled database test.


### 10. AI message insertion must enforce conversation ownership for administrators too

A static review of migration 014 found that the restrictive authenticated INSERT policy for `ai_messages` allowed the organization-admin branch to bypass the `created_by = auth.uid()` check. That meant an administrator could directly insert a `role='user'` message into another user's conversation, despite the policy comment promising that callers can submit only their own user-role messages.

The source proposal was corrected so every authenticated user-message insert must target a conversation they created; organization-admin status or an active road-asset writer role is checked in addition to that ownership condition. This prevents direct Data API impersonation at the policy level. The catalog regression script now also checks that the authenticated INSERT policy references conversation ownership and `auth.uid()`. This source-level assertion is a guard against removing the ownership predicate, not a substitute for an authenticated integration test. The policy change and assertion have not been applied to production or verified with live JWTs. Add an authenticated integration case proving that an administrator cannot post into another user's conversation before approving the migration.

### 11. Document-chunk policies must enforce parent organization consistency for admins too

A further static review of migration 013 found that its original document-chunk SELECT/INSERT/UPDATE/DELETE policies put `private.is_org_admin(organization_id)` outside the parent-document `EXISTS` condition. That meant an organization admin could bypass the parent lookup for chunk rows, allowing orphaned or cross-organization `document_id` references to be created or updated. The SELECT path could also expose inconsistent chunk records within an organization.

The source proposal was corrected so every chunk operation first requires a parent document whose ID matches `document_chunks.document_id` and whose organization matches `document_chunks.organization_id`; the admin/department authorization check is now inside that parent-match condition. The authorization catalog regression script now checks the parent/organization predicates in all four chunk policies. These are source-level changes only and have not been run against a database. The SQL policy text checks are useful regression guards but do not replace JWT integration tests or prove all policy semantics.

## Safe next steps

1. Reconcile the repository migration files with the applied production migration ledger; assign unique ordered identifiers to new migrations.
2. Review function dependencies, grants, and all table/function names against the current schema.
3. Validate the migration sequence in an isolated non-production database with representative authenticated JWTs and test records. Do not use production as the test environment.
4. Run Supabase security advisors and automated authorization catalog checks after test application.
5. Review application smoke tests and a rollback/recovery plan.
6. Only after explicit approval, schedule and apply the approved production migrations, then verify schema, grants, RLS policies, API behavior, and logs.

## Safety record

- Production access during this review: read-only.
- Migrations applied: none.
- Production data modified: none.
- PR #1: remains open and unmerged.
- Do not claim actual-user RLS validation until the authenticated-user matrix has been run against an isolated test database.
