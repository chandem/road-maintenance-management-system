# Production migration checklist (department / RLS proposals)

**Branch:** `feature/department-role-management`  
**Last JWT integration gate:** GitHub Actions run for commit `b8fe659` — Isolated Supabase migration integration test **passed** (migrations apply, catalog checks, department RLS behavior, real Auth-issued JWT PostgREST smoke, release preflight).

This checklist is for a **future, explicitly approved** production rollout. It does **not** authorize applying migrations now.

---

## Safety rules (non-negotiable)

1. Do **not** apply repository files `011`–`018` by filename alone.
2. Do **not** replay production ledger entries already applied (`seed_core_departments_011` … `department_access_helper_015`).
3. Do **not** use production credentials in local/CI tests.
4. Do **not** create paid staging resources without explicit owner approval.
5. Do **not** merge PR #1 until this checklist is complete and signed off.
6. Prefer timestamped, forward-only migration versions in the deployment system.

---

## A. Source and ledger reconciliation

- [ ] Confirm production ledger still ends at the known applied versions (through `department_access_helper_015`).
- [ ] Treat `docs/recovered-migrations/*` as evidence of **already applied** SQL, not as scripts to re-run.
- [ ] Map each **new** proposal (`011_department_road_rls` … `018_profile_and_role_privilege_hardening`) to a **new** unique timestamped version **after** the current ledger tip.
- [ ] Diff each proposal against live catalog (functions, policies, grants, columns) so nothing assumes objects that already differ in production.

## B. Isolated validation (required before production)

Already exercised on disposable local Supabase CI:

- [x] Clean migration apply of repository SQL sequence
- [x] Authorization catalog checks
- [x] Department RLS behavior checks (synthetic claims)
- [x] Real local Auth Admin–provisioned users + password-grant JWTs against PostgREST
- [x] Read-only release preflight script

Still required outside disposable CI (if owner provides an approved non-production project):

- [ ] Replay the same sequence on an approved isolated non-production project
- [ ] Optional workflow_dispatch staging JWT smoke (real user tokens, **never** production project `firzbqzbezuecvplsibi`)
- [ ] Backend service-role paths: assistant message write, document ingest, ranking
- [ ] Frontend onboarding RPC + department-aware UI paths

## C. Proposed apply order (staging first)

1. `011_department_road_rls.sql` — helper move + road RLS  
2. `012_department_module_rls.sql` — module RLS  
3. `013_department_aware_document_access.sql` — `documents.department_code` + chunk policies  
4. `014_ai_conversation_department_rls.sql` — conversation tables + policies  
5. `015_road_section_organization_integrity.sql` — preflight/backfill/triggers  
6. `016_revoke_excess_authenticated_table_privileges.sql`  
7. `017_harden_function_execution_privileges.sql`  
8. `018_profile_and_role_privilege_hardening.sql`  

Before step 5, run `database/tests/road_section_organization_preflight.sql` and require zero blockers.

## D. Production cutover

- [ ] Maintenance window and rollback owner assigned
- [ ] Database backup / PITR recovery point confirmed
- [ ] Apply only the **reviewed timestamped** versions (not ad-hoc SQL editor dumps)
- [ ] Re-run Security Advisor; triage any remaining DEFINER/grant findings
- [ ] Smoke: org admin, road manager, read-only, finance, other-org isolation
- [ ] Smoke: document department isolation + conversation ownership
- [ ] Backend health + one office-assistant and document Q&A call
- [ ] Record applied versions and commit SHA in the ops log

## E. Explicit non-goals of the JWT CI pass

A green disposable CI run proves the **repository clean-install sequence** and **Auth-issued JWT RLS behavior** on local Supabase. It does **not** prove:

- Exact equivalence with the live production schema/ledger
- Backend/UI compatibility on deployed Render/Vercel
- Staging data volume or historical road-section integrity cases

---

## Current recommendation

**Hold production migration apply.**  
**Hold PR merge** until owner sign-off after reviewing this checklist and any remaining staging gates.  
Next engineering step: keep PR #1 draft; optionally run approved non-production validation; only then schedule production.
