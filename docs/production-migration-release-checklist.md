# AI-RMMS Production Migration Release Checklist

Status: **PREPARATION ONLY — no production migrations authorized or applied**

Target Supabase project: `firzbqzbezuecvplsibi`  
Working branch: `test/onboarding-rpc-regression`  
Target branch: `feature/department-role-management`

## 1. Current verified state

- Production migration history previously inspected: 13 entries, through the recovered onboarding RPC and department-access migrations.
- Source migrations 016–020 are hardening proposals that have not been confirmed applied to production.
- Migration 021 reconciles the onboarding RPC with the recovered production behavior.
- CI on the current branch has passed backend tests, SQL syntax checks, and the disposable local Supabase migration integration job.
- The staging real-user-JWT job is skipped because staging credentials are not configured; local CI-issued JWT coverage is exercised separately.
- No production schema or data was changed by this branch work.

## 2. Mandatory pre-release blockers

- [ ] Reconcile the production migration ledger with repository migration filenames and contents. Production contains timestamped migration versions while the repository contains numbered migration files; do **not** run a blind `supabase db push` until the mapping is understood.
- [ ] Review the exact SQL diff for migrations 016–021 against the production schema and existing policies/grants.
- [ ] Confirm the deployed frontend signup/profile-bootstrap flow works with the migration 018 restriction to authenticated profile INSERT(id, full_name) and UPDATE(full_name).
- [ ] Confirm an organization administrator can still manage memberships and department roles using a real authenticated JWT.
- [ ] Verify that migration 021's SECURITY DEFINER RPC is executable by `authenticated` only (apart from function owner semantics), and not by `PUBLIC`, `anon`, or `service_role`.
- [ ] Investigate the Supabase leaked-password-protection advisor warning separately; it is an Auth configuration change, not a SQL migration.
- [ ] Confirm a current database backup/PITR restore point and a tested rollback/recovery plan before any production write.

## 3. Proposed migration order

1. 016 — remove unnecessary TRUNCATE/REFERENCES/TRIGGER table privileges.
2. 017 — harden function execution grants and search paths.
3. 018 — restrict profile and role-assignment privileges.
4. 019 — replace recursive profile-update policy with an ownership-based policy.
5. 020 — revoke anonymous department-role table and column privileges.
6. 021 — reconcile the onboarding RPC body and execution grants.

Do not assume this order is safe for production merely because the disposable database CI passes. The first production rollout should be a reviewed, controlled release after the blockers above are closed.

## 4. Required post-migration verification

- [ ] Confirm each intended migration is recorded exactly once in the production migration ledger.
- [ ] Confirm anonymous requests cannot read or mutate `user_department_roles`.
- [ ] Confirm authenticated non-admin users cannot assign department roles or edit protected profile fields.
- [ ] Confirm authenticated organization admins can assign/revoke department roles and manage organization membership.
- [ ] Confirm the onboarding RPC rejects anonymous calls, duplicate organization codes, and users already assigned to an organization.
- [ ] Confirm successful onboarding creates an active `admin` membership and sets `user_profiles.is_active = true`.
- [ ] Re-run relevant read-only privilege, policy, function-definition, and advisor checks; document any accepted warnings.

## 5. Release decision

**Current decision: NOT READY for production application.**  
Reason: CI is green, but migration-ledger reconciliation and authenticated workflow verification remain release blockers.

This checklist does not authorize production changes. Obtain explicit approval for a specific production migration plan before applying any migration.
