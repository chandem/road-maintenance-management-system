# Production Security Advisor Snapshot

**Project:** `firzbqzbezuecvplsibi`  
**Observed:** 2026-10-10 (latest Supabase advisor observations timestamped 09:25:13 UTC)  
**Branch:** `feature/department-role-management`  
**Purpose:** Record read-only security findings for follow-up; not an authorization validation report.

## Read-only security advisor findings

The Supabase security advisor reported these findings:

1. **Public SECURITY DEFINER department-role helper**
   - Function: `public.has_department_role(uuid, text, text[])`
   - The advisor reports it is executable by both `anon` and `authenticated`.
   - Risk: it is exposed as a Data API RPC and runs with definer privileges. Its exact live body and effective grants must be reconciled against the production migration history before choosing a fix.

2. **Authenticated organization-creation RPC**
   - Function: `public.create_organization_for_current_user(text, text)`
   - The advisor reports authenticated users can execute it as a SECURITY DEFINER function.
   - This may be intentional for onboarding, but the function body, ownership checks, search_path, and grants must be verified before deciding whether any grant changes are appropriate.

3. **Leaked-password protection disabled**
   - Supabase Auth advisor reports leaked-password protection is disabled.
   - This is an Auth configuration follow-up, separate from the unresolved migration-source mapping.

## Migration-history status

The read-only migration ledger still reports 13 applied migrations, including the five department/role entries whose exact source SQL has not been recovered:

- `seed_core_departments_011`
- `create_department_role_assignments_012`
- `secure_department_role_assignments_013`
- `department_role_policies_014`
- `department_access_helper_015`

Do not assume proposed repository migrations with similar numbering or functionality are identical to these applied scripts.

## Safe next actions

1. Recover exact SQL/deployment records for the five unresolved ledger entries.
2. Compare the live function signatures, definitions, SECURITY DEFINER/INVOKER modes, `search_path`, and grants with the recovered SQL using supported read-only inspection.
3. Review whether the onboarding RPC is intentionally callable by authenticated users and confirm its internal authorization guard.
4. Review the leaked-password protection setting with the project owner before changing Auth configuration.
5. Test any proposed remediation only in an already available isolated non-production database. Do not create a paid branch/resource.

## Verification boundary

- No production writes or migrations were performed.
- No RLS integration test with authenticated JWTs was run.
- A read-only query against the Supabase unified logs tool returned a backend error, so no deployment SQL was recovered from logs in this review.
- Advisor findings are warnings requiring review; they are not proof that a specific exploit was exercised.
- CI success does not establish database authorization correctness.

## Additional live catalog inspection (read-only)

A follow-up read-only query through `information_schema.routines` and `information_schema.routine_privileges` returned these live observations:

- `public.has_department_role` is currently `SECURITY DEFINER`. Its visible definition checks `auth.uid()`, an active `user_department_roles` assignment, a matching department in the same organization, and active organization membership; it also checks the requested role array. The routine privilege view lists EXECUTE for `anon`, `authenticated`, `service_role`, and `postgres`.
- `public.create_organization_for_current_user` is currently `SECURITY DEFINER`. Its visible definition rejects a null `auth.uid()`, blank organization names, users whose profile already has an organization, and duplicate non-empty organization codes. It creates the organization, an active admin membership, and a profile association. The routine privilege view lists EXECUTE for `authenticated`, `service_role`, and `postgres`.
- `private.is_org_admin` and `private.is_org_member` are also `SECURITY DEFINER`; their visible definitions check the caller's active organization membership, and admin/owner role for the former. The routine privilege view lists EXECUTE for `authenticated` and `postgres`.

These are observations of the current live definitions and grants, not proof that the original migration source has been recovered. The catalog query did not verify function-level `search_path` configuration, inherited PUBLIC privileges, or behavior under real authenticated JWT requests. Do not change grants based only on this snapshot; reconcile them with the exact applied migration SQL and intended backend flows first.

## Latest advisor recheck — 2026-10-10 09:25:13 UTC

A fresh read-only Supabase security-advisor query at 09:25:13 UTC returned the same three warning categories:

- `public.has_department_role(uuid, text, text[])` is flagged as executable by `anon` and `authenticated` while SECURITY DEFINER.
- `public.create_organization_for_current_user(text, text)` is flagged as executable by `authenticated` while SECURITY DEFINER.
- Leaked-password protection remains disabled.

The migration ledger was also re-read and still reports 13 applied migrations; the five department/role entries remain without recovered exact source SQL. Searches of repository commit history for their migration labels and helper names did not recover matching commits. No production changes were made. These findings remain open until the exact applied SQL is reconciled and a reviewed remediation is tested outside production. The onboarding RPC may be intentionally callable by authenticated users, but its grants and guard must be validated against the recovered source and application flow.

## CI and deployment status — latest checked commit

The latest documentation commit checked was `c4a9283214e026b1a0ebab3f967ed8c08d03f039` (`docs: keep advisor CI note commit-agnostic`). GitHub Actions workflow-run lookup returned successful completed runs for both workflows:

- [Backend Tests](https://github.com/chandem/road-maintenance-management-system/actions/runs/38041372092)
- [Frontend Build](https://github.com/chandem/road-maintenance-management-system/actions/runs/38041372083)

The combined commit status still reports Vercel status-check failures due to the free-plan daily deployment limit (`api-deployments-free-per-day`). PR comments also show earlier preview deployments as Ready, so this limit failure should not be described as proof that all previews are unavailable. GitHub Actions success does not validate production RLS or database migration correctness.
