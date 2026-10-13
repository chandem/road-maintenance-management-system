# Production reconciliation — Step 41

Date: 2026-10-10  
Repository: `chandem/road-maintenance-management-system`  
Branch: `feature/department-role-management`  
Production Supabase project: `ai-rmms` (`firzbqzbezuecvplsibi`)  
Status: **read-only audit completed; production migration rollout remains blocked**

## What was verified

- Production database is PostgreSQL 17.11.
- The live migration ledger contains 13 entries; latest version is `20261009115736` (`department_access_helper_015`).
- The latest isolated GitHub Actions migration integration job passed: migrations applied to disposable local Supabase, Python smoke-test syntax validation passed, authorization catalog checks passed, and release preflight passed.
- No Supabase development branches exist for this project. No new project/branch was created.
- The production audit used read-only SQL only. No production DDL or DML was executed in this step.

## Live schema facts

Present: core roads, road sections, inspections, module tables, documents, document chunks, department/organization membership tables, user profiles, and role assignments.

Absent:
- `public.ai_conversations`
- `public.ai_messages`
- `public.ai_message_sources`
- `public.documents.department_code`

These are migration dependencies, not proof that the proposed SQL is safe to apply without staging validation.

## Road-section preflight

Read-only result:
- Total road sections: 0
- NULL section organization IDs: 0
- Orphaned sections: 0
- Parent roads without an organization: 0
- Organization mismatches: 0

This is a vacuous integrity result because there are no section rows. It does **not** validate migration 015's trigger/backfill behavior with valid, invalid, and cross-organization fixtures.

## Function/security observations

The current production onboarding RPC is owned by `postgres`, is SECURITY DEFINER, uses `search_path=public, pg_catalog`, and is executable by `authenticated` and `service_role`. Its body inserts an organization, an `admin` membership, and a profile row transactionally. The proposed migration 017 must not overwrite this live body without a tested, schema-qualified replacement.

The current public `has_department_role(uuid,text,text[])` is SECURITY DEFINER with an empty search path and is executable by `anon`, `authenticated`, and `service_role`. The Security Advisor reports this as a warning. The proposed 011 wrapper/private-helper conversion is a high-priority security fix, but it must first be tested for policy invocation and PostgREST behavior using real authenticated JWTs.

The current organization-membership policies are permissive. New department policies are designed to be restrictive, so they must be tested in combination with existing policies. Current `documents` and `document_chunks` policies authorize at organization scope; department-level policies remain absent.

## Release decision

**Do not apply migrations 011–018 to production yet.** CI's disposable database is not an isolated staging project with real Auth users and user JWTs. There is no verified staging project available in the connected Supabase account, and no development branch exists on production. Existing inactive Supabase projects are unrelated applications and must not be repurposed or reset without explicit approval.

## Fastest safe next actions

1. Provision/identify an isolated non-production Supabase project with permission to discard/reset it; use synthetic data only. Avoid a paid branch/resource unless separately approved.
2. Apply proposals 011–018 in dependency order to that staging project, stopping at the first SQL error.
3. Seed at least two organizations and real staging Auth users with admin, road manager/officer/read-only, finance-only, unassigned, inactive, and cross-organization identities.
4. Execute the JWT/Data API matrix in `database/tests/department_rls_test_plan.md`, including document/semantic retrieval, onboarding, message integrity, and road-section trigger cases.
5. Review the staging Security Advisor and backend/frontend smoke tests.
6. Reconcile the exact tested SQL against production, prepare a backup/recovery plan and unique timestamped forward-only migration versions, then execute the approved rollout and re-check the production ledger/catalog.

## Safety boundary

The user's request to prioritize production migrations is acknowledged. This report is preparation only and does not authorize bypassing the authenticated-user staging gate. Production remains unchanged by this step.
