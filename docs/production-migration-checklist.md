# Production migration checklist (department / RLS proposals)

**Branch:** `feature/department-role-management`  
**Companion map:** `docs/production-ledger-proposal-map.md`  
**Security gate log:** `docs/security-gate-status.md`

**Last disposable CI gate:** integration on `6655350` — migrations, catalog, RLS behavior, Auth-issued JWT PostgREST, preflight **all pass**.

This checklist is for a **future, explicitly approved** production rollout. It does **not** authorize applying migrations now.

---

## Safety rules (non-negotiable)

1. Do **not** apply repository files `011`–`018` by filename alone.
2. Do **not** replay production ledger entries already applied (`seed_core_departments_011` … `department_access_helper_015`) or anything under `docs/recovered-migrations/`.
3. Do **not** use production credentials in local/CI tests.
4. Do **not** create paid staging resources without explicit owner approval.
5. Do **not** merge PR #1 until this checklist is complete and signed off.
6. Prefer timestamped, forward-only migration versions **after** ledger tip `20261009115736` (unless tip has advanced — re-check first).

---

## A. Source and ledger reconciliation

- [ ] Confirm production ledger tip (expect `department_access_helper_015` / `20261009115736` unless newer exists).
- [ ] Re-read `docs/production-ledger-proposal-map.md` name-collision table with the release engineer.
- [ ] Treat recovered SQL as **applied evidence**, not runnable deploy scripts.
- [ ] Map each repo proposal `011`–`018` to a **new** unique timestamp after the tip.
- [ ] Diff live `has_department_role` (DEFINER public) vs proposal 011 (private + INVOKER wrapper).
- [ ] Confirm live still lacks `documents.department_code` and AI conversation tables before planning 013/014.

## B. Isolated validation

### Disposable local Supabase CI (done)

- [x] Clean migration apply of repository SQL sequence
- [x] Authorization catalog checks
- [x] Department RLS behavior checks (synthetic claims)
- [x] Real local Auth Admin–provisioned users + password-grant JWTs against PostgREST
- [x] Read-only release preflight script
- [x] Backend tests / frontend build / SQL syntax on the same PR head

### Optional owner-approved non-production project

- [ ] Replay proposal sequence with **new** timestamps only
- [ ] Optional workflow_dispatch staging JWT smoke (**never** project `firzbqzbezuecvplsibi`)
- [ ] Backend service-role paths: assistant message write, document ingest, ranking
- [ ] Frontend onboarding RPC after 017/018 search_path and grant changes

## C. Proposed apply order (staging first)

1. `011_department_road_rls.sql` — private helper + road RLS  
2. `012_department_module_rls.sql` — module RLS  
3. `013_department_aware_document_access.sql` — `department_code` + document policies  
4. `014_ai_conversation_department_rls.sql` — conversation tables + policies  
5. `015_road_section_organization_integrity.sql` — after `road_section_organization_preflight.sql` is clean  
6. `016_revoke_excess_authenticated_table_privileges.sql`  
7. `017_harden_function_execution_privileges.sql`  
8. `018_profile_and_role_privilege_hardening.sql`  

## D. Production cutover

- [ ] Maintenance window and rollback owner assigned
- [ ] Database backup / PITR recovery point confirmed
- [ ] Apply only reviewed **timestamped** versions
- [ ] Post-011: PostgREST resolves `public.has_department_role`
- [ ] Post-014: conversation CRUD under real JWTs
- [ ] Post-017/018: onboarding creates org + admin membership; duplicate blocked
- [ ] Re-run Security Advisor; triage DEFINER/grant findings
- [ ] Smoke: org admin, road manager, read-only, finance, other-org isolation
- [ ] Smoke: document department isolation + conversation ownership
- [ ] Backend health + office-assistant + document Q&A
- [ ] Record applied versions and commit SHA in the ops log

## E. What disposable CI does **not** prove

- Exact equivalence with the live production schema/ledger
- Backend/UI compatibility on deployed Render/Vercel
- Non-empty road-section integrity on historical data
- Staging under real network latency/load

---

## Current recommendation

**Hold production migration apply.**  
**Hold PR merge** (keep draft).  
**Best next owner action:** review `docs/production-ledger-proposal-map.md` and either (a) sign off on a non-production validation target or (b) accept disposable CI + checklist as the gate and schedule a later production window with new timestamps only.
