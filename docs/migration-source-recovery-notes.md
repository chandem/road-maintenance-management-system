# Migration Source Recovery Notes

**Branch:** `feature/department-role-management`  
**Repository:** `chandem/road-maintenance-management-system`  
**Review date:** 2026-10-10  
**Status:** Investigative notes only; no production SQL executed.

## Evidence reviewed

### AI assistant schema

The source file `database/migrations/003_ai_assistant.sql` was introduced by commit `cc68c6924c73742eb9259bd48a32013a8fd4fd9e` (“Add AI Office Assistant data foundation”) on 2026-10-07. It creates `public.ai_conversations`, `public.ai_messages`, and `public.ai_message_sources`, plus organization-membership RLS policies.

The read-only production audit found those three tables absent. This means the current live schema does not match the end state expected from that source file. It does **not**, by itself, prove whether the file was never applied, later rolled back, or its objects were subsequently removed. Recover deployment records or the exact applied SQL before assigning a migration status.

The later proposal `database/migrations/014_ai_conversation_department_rls.sql` also creates these tables using `CREATE TABLE IF NOT EXISTS` and adds department-aware restrictions. Do not replay both files blindly: compare table definitions, policies, grants, and their dependencies in a disposable/non-production database first.

### Organization onboarding

The repository contains two distinct onboarding changes:

- `003_onboarding_hardening.sql` defines `private.create_organization_for_current_user(text,text)` and changes a profile update policy.
- `004_frontend_onboarding_rpc.sql` defines `public.create_organization_for_current_user(text,text)` for the frontend and rejects a second organization when the user's profile already has one.

The production ledger label `add_organization_onboarding_rpc` is not sufficient evidence to determine which exact SQL was applied. Compare the live function definitions and grants using supported read-only inspection and recover the deployment SQL/log. Do not assume both source files ran.

### Department and role migration history

The production ledger includes these versions:

- `seed_core_departments_011`
- `create_department_role_assignments_012`
- `secure_department_role_assignments_013`
- `department_role_policies_014`
- `department_access_helper_015`

The repository's `011_department_road_rls.sql` through `015_road_section_organization_integrity.sql` are proposals with different names and purposes; they must not be treated as exact copies of the five applied ledger entries without evidence. The source history search did not recover the exact applied SQL. Mark all five as **unresolved source mapping** until SQL/deployment artifacts are recovered.

## Required recovery checklist

1. Export or locate the exact SQL submitted for each production migration-ledger version and retain its version/name metadata.
2. Compare every recovered script with the corresponding source file: tables/columns, constraints, indexes, functions, function security settings, grants, RLS policies, triggers, and seeds.
3. Mark each source mapping as exact match, partial match, superseded, not applied, or missing—with evidence.
4. Create no paid Supabase branch/resource. Use an already available isolated non-production database only if one is confirmed; otherwise keep testing blocked.
5. Replay only the verified baseline in that isolated database, then apply proposals in dependency order and run catalog checks plus authenticated-JWT tests.
6. Keep production read-only and do not merge the draft PR until this evidence and testing are complete.

## Safety boundary

This document records source review, not a production verification result. No production migration, database write, or RLS integration test was performed. CI success does not establish database authorization correctness.
