# Production migration checklist (department / RLS proposals)

**Branch:** `feature/department-role-management`  
**Companion map:** `docs/production-ledger-proposal-map.md`  
**Security gate log:** `docs/security-gate-status.md`  
**Status reviewed:** 2026-10-13

This checklist is for a **future, explicitly approved** production rollout. It does **not** authorize applying migrations now.

---

## Safety rules

1. Do **not** apply repository files `011`–`018` by filename alone.
2. Do **not** replay applied ledger entries or SQL under `docs/recovered-migrations/`.
3. Do **not** use production credentials in local/CI tests.
4. Do **not** create paid staging resources without explicit owner approval.
5. Do **not** merge PR #1 until all required gates pass and this checklist is signed off.
6. Prefer uniquely timestamped, forward-only migration versions **after** `20261009115736`, but re-check the live ledger before any approved rollout.

---

## A. Source and live-ledger reconciliation

- [x] Read production migration ledger; 13 entries, tip `20261009115736_department_access_helper_015` (checked 2026-10-12).
- [x] Reconcile production ledger names with repository proposal filenames; they are different migrations despite overlapping suffixes.
- [x] Correct outdated documentation claims about live objects.
- [x] Verify `documents.department_code` exists.
- [x] Verify `ai_conversations`, `ai_messages`, and `ai_message_sources` exist.
- [x] Verify RLS is enabled on documents, AI conversation tables, roads, and road sections (FORCE RLS is false).
- [x] Verify `public.has_department_role(uuid,text,text[])` is SECURITY INVOKER, has empty search_path, is executable by authenticated, and is not executable by anon/service_role.
- [x] Confirm authenticated still has TRUNCATE, REFERENCES, and TRIGGER grants on numerous business tables; this is a live privilege gap that proposal 016 is intended to address.
- [ ] Diff all proposed migration SQL against live definitions, policies, constraints, triggers, and grants.
- [ ] Confirm current live ledger tip again before preparing any release versions.

---

## B. Isolated authorization validation

### Disposable local Supabase CI

The security-gate report records passing CI checks for clean migration apply, catalog checks, RLS behavior, Auth Admin provisioning, password-grant JWT/PostgREST smoke, release preflight, backend tests, frontend build, and SQL syntax.

- [x] Clean migration apply of repository SQL sequence in disposable CI
- [x] Authorization catalog checks
- [x] Department RLS behavior checks
- [x] Real local Auth-issued JWT/PostgREST smoke test
- [x] Read-only release preflight
- [x] Backend tests / frontend build / SQL syntax

### Staging limitation

- [ ] Owner-approved non-production Supabase JWT/PostgREST validation
- [ ] Backend service-role paths: assistant message write, document ingest, ranking
- [ ] Frontend onboarding RPC after function/grant changes

The existing `RAMS` project is paused and restoring it requires a paid upgrade. Do not restore it, create paid resources, or change production without explicit approval. Disposable CI is **not** staging and must be described as such.

---

## C. Proposal order for future isolated validation

1. `011_department_road_rls.sql` — compare helper arrangement and road RLS to live definitions.
2. `012_department_module_rls.sql` — compare module RLS to live policies.
3. `013_department_aware_document_access.sql` — live `department_code` and department policies already exist; do not assume this is a missing feature.
4. `014_ai_conversation_department_rls.sql` — AI conversation tables and department policies already exist; compare exact definitions before considering any forward migration.
5. `015_road_section_organization_integrity.sql` — inspect live constraints/triggers and validate non-empty historical rows first.
6. `016_revoke_excess_authenticated_table_privileges.sql` — current catalog confirms excess grants remain on numerous tables; verify the proposal's complete table list before scheduling.
7. `017_harden_function_execution_privileges.sql` — compare exact live function definitions/ACLs and test onboarding compatibility.
8. `018_profile_and_role_privilege_hardening.sql` — test onboarding and role-assignment flows before release.

This is a review/test order, **not** approval to apply these files to production. Any future release must use reviewed, uniquely timestamped migration versions, not original proposal filenames.

---

## D. Production cutover gates (not yet approved)

- [ ] All live-vs-proposal SQL differences documented and reviewed
- [ ] Real Auth-issued JWT matrix passes on a separate, approved non-production target, or an explicit risk-acceptance decision is documented
- [ ] Backend service-role flows and frontend onboarding smoke tests pass
- [ ] Road-section organization integrity preflight passes on non-empty data
- [ ] Maintenance window and rollback owner assigned
- [ ] Backup / PITR recovery point confirmed
- [ ] Only reviewed timestamped versions are applied
- [ ] Post-migration catalog, privilege, RLS, and real-user smoke tests pass
- [ ] Security Advisor findings reviewed
- [ ] Applied versions and commit SHA recorded in operations log

---

## E. Current recommendation

**Hold production migration apply.**  
**Keep PR #1 in draft.**  
Continue read-only catalog audits and source comparison, and use disposable CI for repeatable tests. Do not describe CI as staging. Do not pay for staging, merge PR #1, or apply migrations without explicit approval.
