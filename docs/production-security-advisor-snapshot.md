# Production Security Advisor Snapshot

**Project:** `firzbqzbezuecvplsibi`  
**Observed:** 2026-10-10 (Supabase advisor observations timestamped 09:01:14 UTC)  
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
