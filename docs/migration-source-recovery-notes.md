# Migration Source Recovery Notes

**Branch:** `feature/department-role-management`  
**Repository:** `chandem/road-maintenance-management-system`  
**Review date:** 2026-10-10  
**Status:** SQL source recovered and archived for migrations 011–015. Production remains read-only during reconciliation.

## Latest recovery update — 2026-10-10

The exact SQL bodies for all five department/role migrations were recovered from the production project's PostgreSQL logs and the `supabase_migrations.schema_migrations.statements` records. They are archived under `docs/recovered-migrations/` on this feature branch, intentionally outside the automatic migration directory.

| Version | Name | Archive |
|---|---|---|
| `20261009115651` | `seed_core_departments_011` | `docs/recovered-migrations/20261009115651_seed_core_departments_011.sql` |
| `20261009115706` | `create_department_role_assignments_012` | `docs/recovered-migrations/20261009115706_create_department_role_assignments_012.sql` |
| `20261009115713` | `secure_department_role_assignments_013` | `docs/recovered-migrations/20261009115713_secure_department_role_assignments_013.sql` |
| `20261009115721` | `department_role_policies_014` | `docs/recovered-migrations/20261009115721_department_role_policies_014.sql` |
| `20261009115736` | `department_access_helper_015` | `docs/recovered-migrations/20261009115736_department_access_helper_015.sql` |

The log records show these statements were submitted through the Supabase management API on 2026-10-09. This resolves the earlier uncertainty about where the SQL came from. It does **not** make the draft PR's proposed migration files equivalent to the applied SQL.

### Read-only catalog reconciliation performed

- `public.departments` exists; the partial unique index `departments_org_code_unique` exists.
- The `GRMB` organization has all five department seed rows expected by migration 011: Road Asset Management, Machinery Maintenance Management, Finance, Human Resources, and General Asset Management.
- `public.user_department_roles` exists with the expected primary key, organization/user/department foreign keys, role check constraint, unique organization/user/department constraint, and both indexes introduced by migration 013.
- RLS is enabled on `public.user_department_roles`.
- The two policies from migration 014 exist: `users_can_view_own_department_roles` and `org_admins_manage_department_roles`.
- `public.has_department_role(uuid,text,text[])` exists with the security-definer SQL body and authenticated-only execute grant described by migration 015.
- These catalog checks verify object presence and configuration, **not** authorization behavior under real authenticated JWTs.
- No new production SQL was executed during this recovery.

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

The five applied SQL bodies were recovered and archived as documented above. The repository's `011_department_road_rls.sql` through `015_road_section_organization_integrity.sql` are proposals with different names and purposes; they must not be treated as exact copies of the five applied ledger entries.

## Remaining work

1. Reconcile the exact source for earlier ledger entries, especially organization onboarding, and investigate why the AI assistant tables are absent.
2. Compare the full live schema with all ledger/source migrations and classify each source mapping as matching, partially matching, divergent, superseded, or missing.
3. Use an already available isolated non-production database only if one is confirmed; do not create a paid Supabase branch/resource.
4. Run integration tests with real authenticated JWTs in non-production before considering a production change or merging PR #1.
5. Only after the baseline and authorization tests are reconciled, plan any remaining production migrations with an explicit review of the exact SQL and rollback strategy.

## Safety boundary

Do not rerun, reapply, or edit production migrations to recover their source. Source recovery is an inspection task, not a database change. Keep production read-only until source mapping, schema reconciliation, and authenticated authorization tests are complete.
