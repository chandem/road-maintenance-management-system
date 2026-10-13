# Production Migration Reconciliation — 2026-10-13

## Scope
Repository: `chandem/road-maintenance-management-system`
Branch reviewed: `feature/department-role-management`
Supabase project: `firzbqzbezuecvplsibi`

This report is read-only evidence for release planning. It does not authorize or perform production changes.

## Production migration ledger
The production ledger currently contains 13 records:

1. `20261008122917 initial_ai_rmms_schema`
2. `20261008123128 document_intelligence`
3. `20261008123135 document_embeddings`
4. `20261008140938 authorization_foundation`
5. `20261008141032 secure_semantic_search`
6. `20261008183919 add_organization_onboarding_rpc`
7. `20261009092658 materials_inventory_009`
8. `20261009092727 road_inspections_010`
9. `20261009115651 seed_core_departments_011`
10. `20261009115706 create_department_role_assignments_012`
11. `20261009115713 secure_department_role_assignments_013`
12. `20261009115721 department_role_policies_014`
13. `20261009115736 department_access_helper_015`

## Confirmed production state
Read-only catalog checks confirmed:
- `public.user_department_roles` has RLS policies for organization-admin management and users viewing their own assignments.
- The table ACL grants `anon` table-level DELETE, INSERT, MAINTAIN, REFERENCES, SELECT, TRIGGER, TRUNCATE, and UPDATE.
- The `authenticated` role also has broad table-level privileges on `user_department_roles`, including structural privileges that should be reviewed and narrowed.
- Information-schema checks also show direct anonymous column-level SELECT, INSERT, UPDATE, and REFERENCES privileges across the department-role columns.
- Production has `documents.department_code`, the AI conversation/message/source tables, and a road-section organization-integrity trigger; road-section organization ownership is NOT NULL.
- `public.create_organization_for_current_user(text,text)` is SECURITY DEFINER but its current search path is `public, pg_catalog`; its body assigns organization membership role `admin`, and its ACL grants EXECUTE to `authenticated` and `service_role`.
- Repository migration `003_onboarding_hardening.sql` instead defines `private.create_organization_for_current_user`, sets an empty search path, assigns role `owner`, and grants EXECUTE to `authenticated`. This is a material mismatch and must be reconciled with real application/backend behavior before changing either function.

## Repository source reconciliation
The exact SQL bodies for production ledger migrations 011–015 have since been recovered from production migration statements/logs and archived as evidence under `docs/recovered-migrations/`. They are intentionally outside `database/migrations/` so clean-install automation will not mistake evidence archives for new migrations. They must still be compared semantically with the current proposed migration sequence; do not replay them or assume the proposal files are equivalent.

Repository proposals present on the reviewed branch:
- `database/migrations/018_profile_and_role_privilege_hardening.sql`
- `database/migrations/019_fix_recursive_profile_update_policy.sql`
- `database/tests/authorization_catalog_checks.sql`
- `database/tests/migration_release_preflight.sql`

The isolated migration integration workflow passed at commit `628795531b507187e93b6f62a367b3fca6deb18e`, including clean-install migrations, authorization catalog checks, RLS behavior checks, local Auth-issued JWT Data API tests, and read-only release preflight. Backend tests, frontend build, and SQL syntax checks also passed for that commit. The real staging Data API test was skipped because staging credentials/configuration were not available. These tests do not prove production equivalence.

## Release blockers
1. Recover or formally reconstruct the source for migrations 011–015 and reconcile each definition against the live catalog.
2. Identify and validate the source of current table/column grants on `user_department_roles`; test revocations against authenticated administrator workflows.
3. Reconcile the organization-onboarding RPC schema, function body, search path, grants, and owner/admin semantics with application behavior.
4. Validate profile signup/bootstrap and full-name editing after the profile column-grant proposal.
5. Run authenticated-JWT/Data API tests against a non-production environment. Local CI alone is insufficient.
6. Re-run read-only preflight and review the exact ordered production migration plan, expected effects, and rollback/recovery plan.

## Deployment status
No production schema or data changes were made during this review. Do not apply migrations 016–019 or any reconstructed migration to production until the blockers above are resolved and the production change set has been explicitly approved.


## Follow-up read-only verification — 2026-10-13

A fresh catalog query reconfirmed that production still has 13 migration ledger entries; migrations 016–020 are not recorded as applied. It also reconfirmed effective privileges on `public.user_department_roles`: `anon` has table-level SELECT, INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, and TRIGGER privileges; `authenticated` has TRUNCATE, REFERENCES, and TRIGGER. RLS is enabled, but these grants remain excessive and need a tested revocation plan. The proposed migration 020 and its catalog test are source-controlled only.

The current function catalog contains both `private.has_department_role(uuid,text,text[])` (SECURITY DEFINER, empty search path) and `public.has_department_role(uuid,text,text[])` (SECURITY INVOKER, empty search path); both deny anonymous EXECUTE and allow authenticated EXECUTE. The public onboarding RPC remains SECURITY DEFINER with `search_path=public, pg_catalog`, and EXECUTE is granted to authenticated and service_role but not anon. The exact recovered production onboarding statement is archived at `docs/recovered-migrations/20261008183919_add_organization_onboarding_rpc.sql`; it assigns the initial membership role `admin`. These are observations, not authorization behavior tests.

No production schema, grants, functions, or data were changed during this follow-up.
