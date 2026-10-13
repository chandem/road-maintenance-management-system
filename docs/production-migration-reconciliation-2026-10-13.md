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
The expected paths for original migrations 011–015 could not be recovered at the time of this review. The production ledger entries therefore cannot yet be mapped with confidence to exact source-controlled SQL files. Do not recreate historical migration files as if they were the originals; reconstruct only as clearly labelled recovery proposals based on catalog evidence and verified commit history.

Repository proposals present on the reviewed branch:
- `database/migrations/018_profile_and_role_privilege_hardening.sql`
- `database/migrations/019_fix_recursive_profile_update_policy.sql`
- `database/tests/authorization_catalog_checks.sql`
- `database/tests/migration_release_preflight.sql`

The isolated migration integration workflow passed at commit `bc2eac3996379684aed076f8b06681330fc40b26`. The workflow is not proof of production equivalence; its real staging Data API test was skipped because staging credentials/configuration were not available.

## Release blockers
1. Recover or formally reconstruct the source for migrations 011–015 and reconcile each definition against the live catalog.
2. Identify and validate the source of current table/column grants on `user_department_roles`; test revocations against authenticated administrator workflows.
3. Reconcile the organization-onboarding RPC schema, function body, search path, grants, and owner/admin semantics with application behavior.
4. Validate profile signup/bootstrap and full-name editing after the profile column-grant proposal.
5. Run authenticated-JWT/Data API tests against a non-production environment. Local CI alone is insufficient.
6. Re-run read-only preflight and review the exact ordered production migration plan, expected effects, and rollback/recovery plan.

## Deployment status
No production schema or data changes were made during this review. Do not apply migrations 016–019 or any reconstructed migration to production until the blockers above are resolved and the production change set has been explicitly approved.
