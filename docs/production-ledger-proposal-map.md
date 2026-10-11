# Production ledger ↔ repository proposal map

**Branch:** `feature/department-role-management`  
**As of:** 2026-10-11  
**Purpose:** Prevent accidental re-application of already-applied SQL and clarify what remains to ship.

**Safety:** Recovered files under `docs/recovered-migrations/` are **evidence only**. Do not replay them against production.

---

## 1. Name collision warning

Production ledger **names** end in `_011` … `_015`. Repository proposal **filenames** also start at `011_…`.  
**They are not the same migrations.**

| Production ledger (applied) | Repository proposal (not applied) |
|-----------------------------|-----------------------------------|
| `seed_core_departments_011` | `011_department_road_rls.sql` |
| `create_department_role_assignments_012` | `012_department_module_rls.sql` |
| `secure_department_role_assignments_013` | `013_department_aware_document_access.sql` |
| `department_role_policies_014` | `014_ai_conversation_department_rls.sql` |
| `department_access_helper_015` | `015_road_section_organization_integrity.sql` |

Any production apply of repository `011`–`018` must use **new unique timestamps after** `20261009115736`.

---

## 2. Applied production ledger (department/role slice)

| Ledger version | Ledger name | Archive | What it did |
|----------------|-------------|---------|-------------|
| `20261009115651` | `seed_core_departments_011` | `docs/recovered-migrations/20261009115651_seed_core_departments_011.sql` | Unique `(organization_id, code)` on departments; seed five GRMB departments |
| `20261009115706` | `create_department_role_assignments_012` | `…_012.sql` | Create `user_department_roles` table/constraints |
| `20261009115713` | `secure_department_role_assignments_013` | `…_013.sql` | Indexes + enable RLS on assignments |
| `20261009115721` | `department_role_policies_014` | `…_014.sql` | View-own + org-admin manage policies |
| `20261009115736` | `department_access_helper_015` | `…_015.sql` | `public.has_department_role` **SECURITY DEFINER**, `search_path = ''`, execute for `authenticated` only |

Also recovered (related, not department-role numbered):

| Ledger version | Name | Archive |
|----------------|------|---------|
| `20261008183919` | `add_organization_onboarding_rpc` | `docs/recovered-migrations/20261008183919_add_organization_onboarding_rpc.sql` |

Live production helper state (from recovery notes): `public.has_department_role` is DEFINER with empty search path — **not** yet moved to `private` with an INVOKER public wrapper.

---

## 3. Repository proposals still to ship (after new timestamps)

| Repo file | Intent | Depends on | Production gap it closes |
|-----------|--------|------------|--------------------------|
| `010_department_role_foundation.sql` | Foundation if clean-install only | Earlier core | Clean CI install path; production already has role objects via ledger 011–015 |
| `011_department_road_rls.sql` | Move helper to `private` + INVOKER wrapper; restrictive road/section/inspection RLS | Live `has_department_role` | Department isolation on road data |
| `012_department_module_rls.sql` | Restrictive module RLS | 011 helpers | Module isolation |
| `013_department_aware_document_access.sql` | `documents.department_code` + dept document/chunk policies | 011–012 | Live has org-only document policies; no `department_code` |
| `014_ai_conversation_department_rls.sql` | Create AI conversation tables + ownership policies | 011 helpers | Live missing `ai_conversations` / `ai_messages` / `ai_message_sources` |
| `015_road_section_organization_integrity.sql` | Backfill/triggers for section org integrity | Road data | Nullable section org IDs |
| `016_revoke_excess_authenticated_table_privileges.sql` | Revoke TRUNCATE/REFERENCES/TRIGGER | Tables from 014 present | Excess grants on many public tables |
| `017_harden_function_execution_privileges.sql` | Function ACL + empty search_path | 011 private helper + onboarding RPC | Defense in depth |
| `018_profile_and_role_privilege_hardening.sql` | Column-level profile/role grants | Onboarding still works | Direct profile write surface |

**Clean-install CI** applies `001`–`018` in filename order on a disposable DB. That validates the *proposal sequence*, not production ledger identity.

---

## 4. Known live vs proposal divergences

| Area | Live production | Repo proposal |
|------|-----------------|---------------|
| `has_department_role` | `public`, SECURITY DEFINER | 011 moves body to `private`, public INVOKER wrapper |
| Document access | Org-member policy only; no `department_code` | 013 adds department scoping |
| AI conversation tables | Absent | 014 creates them |
| Onboarding RPC | Recovered SQL: role `admin`, `search_path=public, pg_catalog` | `004` / 017 differ (owner vs admin, search_path hardening) |
| TRUNCATE on `authenticated` | Present on many tables | 016 revokes |

---

## 5. Recommended production apply strategy (when approved)

1. **Do not** insert recovered `20261009*` SQL again.  
2. Confirm ledger tip is still `20261009115736` (or note any newer applied versions).  
3. On staging (owner-approved only): apply **new** timestamps for repo `011`→`018` in order.  
4. Re-run catalog + Auth JWT matrix.  
5. Especially verify after 011: PostgREST still resolves `public.has_department_role`; after 017/018: onboarding still creates org + membership.  
6. Only then schedule production with backup/PITR and the same timestamped SQL.

---

## 6. CI evidence (disposable, not production)

| Gate | Status |
|------|--------|
| Migration apply | Pass |
| Catalog checks | Pass |
| Department RLS behavior | Pass |
| Auth Admin provision + password-grant JWT PostgREST | Pass |
| Release preflight | Pass |

Latest green integration example: Actions run on `6655350` (PR workflow #96).

---

## 7. Owner decision required

| Decision | Default until explicit yes |
|----------|----------------------------|
| Create paid Supabase branch | **No** |
| Apply proposals to production | **No** |
| Merge PR #1 | **No** (remain draft) |
| Use existing free/non-prod project for extra validation | Owner must name the project |
