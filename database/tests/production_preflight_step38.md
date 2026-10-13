# Production migration preflight — Step 38

Date: 2026-10-10  
Production project: `firzbqzbezuecvplsibi` (`ai-rmms`)  
Branch: `feature/department-role-management`  
Scope: read-only Supabase Security Advisor + migration ledger + staging availability check  
**No production schema or data changes were made.**

## Fresh production checks

### Migration ledger

The live ledger still contains 13 migrations and ends at:

- `20261009115736` — `department_access_helper_015`

The proposed source migrations 011–018 are not represented by matching names in the live ledger and must not be blindly replayed by filename or guessed version. The production baseline and migration SQL must be reconciled explicitly.

### Security Advisor findings

The live Security Advisor currently reports:

1. **High-priority remediation before department-level release:** `public.has_department_role(uuid,text,text[])` is still `SECURITY DEFINER` and executable by `anon` and `authenticated` through the public RPC endpoint. This is the exact live finding migration 011/017 intends to address. Do not treat the proposed migration as applied until the catalog and Data API verify the result.
2. **Organization onboarding RPC:** `public.create_organization_for_current_user(text,text)` is a callable `SECURITY DEFINER` function for authenticated users. This may be intentional because it provisions the first organization, membership, and profile. Keep it only if the authenticated onboarding test passes and the function's body, search path, and ACL are reviewed. Migration 017 proposes removing `service_role` execution and setting an empty search path.
3. **Leaked password protection disabled:** Supabase Auth reports compromised-password checking is disabled. This is an Auth configuration follow-up, not a SQL migration. Enable it through the supported Auth settings after assessing user impact.

Official remediation references:
- Supabase database linter finding 0028: https://supabase.com/docs/guides/database/database-linter?lint=0028_anon_security_definer_function_executable
- Supabase database linter finding 0029: https://supabase.com/docs/guides/database/database-linter?lint=0029_authenticated_security_definer_function_executable
- Supabase Auth password security: https://supabase.com/docs/guides/auth/password-security#password-strength-and-leaked-password-protection

### Staging availability

The production project currently has no Supabase development branches. The connected account lists other inactive Supabase projects, but they belong to separate apps and are not verified clean baselines for AI-RMMS. Do not repurpose them or create a potentially billable resource without explicit user permission.

## Release decision

**Production migrations remain blocked.** The new Security Advisor result reinforces that helper hardening is still outstanding. Applying migrations 011–018 to production without first running the role matrix could cause either data exposure or loss of required application access.

Required sequence:
1. Identify an existing non-production AI-RMMS database or obtain explicit approval to provision an isolated staging environment after its cost is shown.
2. Reconcile its schema and ledger to the production baseline.
3. Apply migrations 011–018 in the proposed dependency order only in staging.
4. Run `database/tests/authorization_catalog_checks.sql` and `database/tests/migration_release_preflight.sql`.
5. Execute `database/tests/department_rls_test_plan.md` with real user JWTs for organization admin, each department/role, read-only, unassigned, inactive member, and cross-organization user.
6. Test organization signup/profile bootstrap, document upload/retrieval/semantic search, AI conversations, road/section/inspection CRUD, and backend/frontend smoke flows.
7. Re-run Security Advisor and review every remaining finding.
8. Prepare a production-specific, ordered migration bundle and rollback/verification checklist. Ask for explicit production rollout approval before any production DDL.

## Current milestone

- Production catalog / migration ledger rechecked: complete.
- Security Advisor rechecked: complete.
- Staging environment: not yet available/verified.
- Authenticated-JWT authorization matrix: pending.
- Production rollout: not authorized and not executed.
